import pandas as pd
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from pathlib import Path
import asyncio
import os
import json
import re
from datetime import datetime
from typing import Dict, Optional, Tuple
import random
import time

# Création du dossier screenshots et ses sous-dossiers
SCREENSHOTS_DIR = Path("screenshots")
FULL_PAGE_DIR = SCREENSHOTS_DIR / "full_page"
CONTENT_DIR = SCREENSHOTS_DIR / "content_page"

# Fichier pour stocker les URLs échouées
FAILED_URLS_FILE = SCREENSHOTS_DIR / "failed_urls.csv"

# Messages d'erreur connus
ERROR_PATTERNS = {
    'captcha': re.compile(r'captcha|cloudflare|human verification|are you human', re.IGNORECASE),
    'timeout': re.compile(r'timeout|timed out|time exceeded', re.IGNORECASE),
    'not_found': re.compile(r'404|not found|page missing', re.IGNORECASE),
    'access_denied': re.compile(r'403|access denied|forbidden', re.IGNORECASE)
}

# Création des dossiers nécessaires
for dir in [SCREENSHOTS_DIR, FULL_PAGE_DIR, CONTENT_DIR]:
    dir.mkdir(exist_ok=True)

# Configuration générale
EXCEL_FILE = 'data-final-part-1.csv'  # Nom du fichier CSV
URL_COLUMN = 'lien_web'  # Nom de la colonne contenant les URLs
ID_COLUMN = 'id'  # Nom de la colonne contenant les IDs

# Configuration des paramètres de capture d'écran
VIEWPORT_SIZE = {'width': 1920, 'height': 8000}
MIN_WAIT_TIME = 2  # délai minimum entre les requêtes
MAX_WAIT_TIME = 5  # délai maximum entre les requêtes
MAX_RETRIES = 3    # nombre maximum de tentatives par URL

# Configuration des délais entre domaines
SAME_DOMAIN_MIN_DELAY = 10  # délai minimum pour le même domaine
SAME_DOMAIN_MAX_DELAY = 15  # délai maximum pour le même domaine
DOMAIN_HISTORY_SIZE = 50    # nombre de domaines à mémoriser

# Liste des sélecteurs de cookies à supprimer
COOKIE_SELECTORS = [
    '#cookie-notice', '.cookie-notice', '#cookieNotice',
    '.cookie-banner', '#cookie-banner', '.cookie-consent',
    '#cookie-consent', '.cookies-popup', '#cookies-popup',
    '[class*="cookie"]', '[id*="cookie"]',
    '[class*="consent"]', '[id*="consent"]',
    '.gdpr', '#gdpr', '[class*="gdpr"]', '[id*="gdpr"]'
]

# Liste des sélecteurs possibles pour le contenu principal des articles
ARTICLE_SELECTORS = [
    # Sélecteurs génériques pour articles
    'article',
    'main article',
    '[role="article"]',
    # Classes communes pour le contenu principal
    '.article-content',
    '.main-content-column',#hibapress.com
    '.jeg_main_content.col-md-8',#ACHTARI24.COM
    '.main-content-left',#FLM.MA
    '.block-area',#ALNOORTV.MA
    '.single-post',#ANFASPRESS.COM 
    '.the-post'#HONA24.NET, ICIAGADIR.COM, ICICASA.COM
    '#main-content > div.content > article', #ACHAMALPRESS.COM
    '.s-ct',#ALJARIDA.MA
    '#main',#eljadida-press
    '#primary',#IHATA.MA
    '.post-content',
    '.entry-content',
    '.article-body',
    '.main-content',
    '.post__content',
    '.story-content',
    # IDs communs
    '#article-content',
    '#main-content',
    '#post-content',
    # Sélecteurs pour les sites arabes
    '.article-desc',
    '.single-article',
    '.post-single',
    '[lang="ar"] article',
    '[lang="ar"] .entry-content',
    # Conteneurs génériques avec attributs semantiques
    'main[role="main"]',
    '[itemprop="articleBody"]',
    '[property="articleBody"]',
    # Fallbacks
    '.content',
    '.main'
]

def categorize_error(error_message: str) -> str:
    """Catégorise l'erreur en fonction des patterns connus."""
    for error_type, pattern in ERROR_PATTERNS.items():
        if pattern.search(error_message):
            return error_type
    return "unknown_error"

async def remove_cookie_popups(page):
    """Supprime les popups de cookies de la page."""
    try:
        for selector in COOKIE_SELECTORS:
            try:
                # Tenter de cliquer sur les boutons d'acceptation courants
                accept_buttons = [
                    'button:has-text("Accepter")', 'button:has-text("Accept")',
                    'button:has-text("Accept all")', 'button:has-text("Tout accepter")',
                    '[id*="accept"]', '[class*="accept"]',
                    'button:has-text("OK")', 'button:has-text("Close")', 'button:has-text("Fermer")'
                ]
                
                for button in accept_buttons:
                    try:
                        await page.click(button, timeout=1000)
                    except:
                        continue

                # Supprimer les éléments de cookie restants
                await page.evaluate(f"""
                    document.querySelectorAll('{selector}').forEach(el => {{
                        el.remove();
                    }});
                """)
            except:
                continue
                
        # Supprimer les styles fixed et sticky qui pourraient bloquer la vue
        await page.evaluate("""
            document.querySelectorAll('*').forEach(el => {
                const style = window.getComputedStyle(el);
                if (style.position === 'fixed' || style.position === 'sticky') {
                    if (el.textContent.toLowerCase().includes('cookie') ||
                        el.textContent.toLowerCase().includes('consent') ||
                        el.textContent.toLowerCase().includes('gdpr')) {
                        el.remove();
                    }
                }
            });
        """)
    except Exception as e:
        print(f"Avertissement lors de la suppression des cookies: {str(e)}")

async def check_for_blocking(page):
    """Vérifie si la page contient des éléments de blocage."""
    blocking_patterns = [
        "//div[contains(text(), 'captcha') or contains(@class, 'captcha')]",
        "//div[contains(text(), 'verify') and contains(text(), 'human')]",
        "//iframe[contains(@src, 'captcha') or contains(@src, 'challenge')]",
        "//div[contains(@class, 'cf-browser-verification')]",
        "//div[contains(@class, 'challenge-running')]"
    ]
    
    for pattern in blocking_patterns:
        if await page.locator(pattern).count() > 0:
            return True
    return False

async def find_article_content(page):
    """Trouve le sélecteur qui correspond au contenu principal de l'article."""
    for selector in ARTICLE_SELECTORS:
        try:
            element = page.locator(selector).first
            if await element.count() > 0:
                # Vérifie si l'élément est visible et a du contenu
                is_visible = await element.is_visible()
                content = await element.text_content()
                if is_visible and content and len(content.strip()) > 100:
                    print(f"Contenu trouvé avec le sélecteur: {selector}")
                    return selector
        except Exception:
            continue
    
    # Fallback sur body si aucun sélecteur spécifique n'est trouvé
    return None

async def capture_screenshots(page, site_id) -> Tuple[bool, Optional[str], Dict[str, str]]:
    """
    Capture les screenshots de la page complète et du contenu de l'article.
    Retourne: (succès, message d'erreur, chemins des captures)
    """
    paths = {"full": "", "content": ""}
    try:
        # Vérifier si la page est bloquée
        if await check_for_blocking(page):
            return False, "Page bloquée par captcha/vérification", paths
        
        # Attendre que la page soit chargée
        await page.wait_for_load_state("networkidle", timeout=30000)
        
        # Capture du contenu principal uniquement
        article_selector = await find_article_content(page)
        if article_selector:
            article_content = page.locator(article_selector).first
            article_path = CONTENT_DIR / f"{site_id}.png"
            
            # Nettoyage des publicités et optimisation avant capture
            await page.evaluate("""(selector) => {
                try {
                    // Suppression des publicités et éléments non désirés
                    const removeAds = () => {
                        try {
                            // Liste des sélecteurs communs pour les publicités
                            const adSelectors = [
                                'iframe:not([title*="article"])',  // Garder les iframes pertinentes
                                '[class*="ads"]:not([class*="article"])',
                                '[id*="ads-"]',
                                '.social-share',
                                '[class*="banner"]',
                                'ins.adsbygoogle',
                                '[class*="newsletter"]'
                            ];

                            adSelectors.forEach(adSelector => {
                                try {
                                    document.querySelectorAll(adSelector).forEach(el => {
                                        if (el && !el.closest(selector)) {
                                            el.remove();
                                        }
                                    });
                                } catch (e) {
                                    console.log('Erreur sur un sélecteur:', e);
                                }
                            });
                        } catch (e) {
                            console.log('Erreur dans removeAds:', e);
                        }
                    };

                    // Nettoyer d'abord, puis attendre les polices
                    removeAds();
                    
                    // Continuer même si document.fonts n'est pas disponible
                    const fontPromise = document.fonts && document.fonts.ready ? 
                        document.fonts.ready : Promise.resolve();
                    return fontPromise.then(() => {
                        const element = document.querySelector(selector);
                        if (element) {
                            try {
                                // Styles de base sécurisés
                                const styles = {
                                    'font-family': 'Arial, sans-serif',
                                    'background-color': '#ffffff',
                                    'color': '#000000',
                                    'margin': '0',
                                    'padding': '20px',
                                    'font-size': '16px',
                                    'line-height': '1.6',
                                    'max-width': '100%',
                                    'width': 'auto',
                                    'text-rendering': 'optimizeLegibility'
                                };

                                // Appliquer les styles de manière sécurisée
                                Object.entries(styles).forEach(([key, value]) => {
                                    try {
                                        element.style[key] = value;
                                    } catch (e) {
                                        console.log(`Erreur style ${key}:`, e);
                                    }
                                });

                                // Scroll en position
                                try {
                                    element.scrollIntoView({block: 'center', inline: 'center'});
                                } catch (e) {
                                    console.log('Erreur scroll:', e);
                                }

                                return true;
                            } catch (e) {
                                console.log('Erreur styles:', e);
                                return false;
                            }
                        }
                        return false;
                    }).catch(() => false);
                } catch (e) {
                    console.log('Erreur principale:', e);
                    return false;
                }
            }""", article_selector)
            
            await asyncio.sleep(1)  # Attendre les animations
            await article_content.screenshot(
                path=str(article_path),
                type='png',
                scale="device"
            )
            
            # Vérification de la capture du contenu
            if not article_path.exists() or article_path.stat().st_size == 0:
                return False, f"Échec de la capture du contenu pour ID {site_id}", paths
            
            paths["content"] = str(article_path)
            print(f"  Capture contenu article sauvegardée: {article_path}")
            return True, None, paths
        else:
            return False, f"Contenu principal non trouvé (ID: {site_id})", paths
            
    except PlaywrightTimeout as e:
        return False, f"Timeout: {str(e)}", paths
    except Exception as e:
        return False, f"Erreur lors de la capture: {str(e)}", paths

async def main():
    """Fonction principale d'exécution du script."""
    start_time = time.time()  # Enregistrer le temps de début
    

    # Lecture du fichier Excel et initialisation du DataFrame pour les URLs échouées
    try:
        df = pd.read_csv(EXCEL_FILE)
        if URL_COLUMN not in df.columns:
            raise ValueError(f"La colonne {URL_COLUMN} n'existe pas dans le fichier")
        print(f"Fichier chargé avec succès. {len(df)} URLs trouvées.")
        
        # Création/chargement du DataFrame pour les URLs échouées
        failed_df = pd.DataFrame(columns=['id', 'url', 'reason'])
        if FAILED_URLS_FILE.exists():
            failed_df = pd.read_csv(FAILED_URLS_FILE)
        
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier : {str(e)}")
        return

    successful = failed = 0
    total_urls = len(df)
    
    async with async_playwright() as p:
        try:
            # Lancement du navigateur avec options optimisées
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process'
                ]
            )
            
            # Contexte avec viewport et options avancées
            context = await browser.new_context(
                viewport={'width': int(VIEWPORT_SIZE['width']), 'height': int(VIEWPORT_SIZE['height'])},
                ignore_https_errors=True,
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            
            # Configuration du contexte
            context.set_default_navigation_timeout(30000)  # 30s timeout
            
            # Ajout de scripts d'interception
            await context.add_init_script("""
                // Désactiver la détection de bot
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                // Simuler des plugins
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            """)
            
            for i, (_, row) in enumerate(df.iterrows()):
                current_index = i + 1
                site_id = str(row[ID_COLUMN])
                url = str(row[URL_COLUMN]).strip()
                
                # Vérifier si l'URL a déjà échoué
                if site_id in failed_df['id'].values:
                    print(f"\n URL déjà échouée précédemment (ID: {site_id}): {url}")
                    failed += 1
                    continue
                
                # Attendre un délai aléatoire avant de traiter l'URL
                wait_time = random.uniform(MIN_WAIT_TIME, MAX_WAIT_TIME)
                print(f"  Attente de {wait_time:.1f} secondes...")
                await asyncio.sleep(wait_time)
                
                print(f"\n➡ Traitement de l'URL {current_index}/{total_urls} (ID: {site_id}): {url}")
                
                try:
                    page = await context.new_page()
                    try:
                        # Navigation avec gestion des timeouts
                        await page.goto(
                            url,
                            wait_until='domcontentloaded',
                            timeout=30000
                        )
                        
                        # Capture des screenshots avec gestion des erreurs
                        success, error_msg, paths = await capture_screenshots(page, site_id)
                        
                        if success:
                            successful += 1
                            print(f"   URL {current_index}/{total_urls} (ID: {site_id}) traitée avec succès")
                        else:
                            failed += 1
                            print(f"   URL {current_index}/{total_urls} (ID: {site_id}) : {error_msg}")
                            
                            # Ajouter l'URL échouée au DataFrame
                            new_failure = pd.DataFrame({
                                'id': [site_id],
                                'url': [url],
                                'reason': [error_msg]
                            })
                            failed_df = pd.concat([failed_df, new_failure], ignore_index=True)
                            
                            # Sauvegarder progressivement les échecs
                            failed_df.to_csv(FAILED_URLS_FILE, index=False)
                    
                    except PlaywrightTimeout as e:
                        error_msg = f"Timeout de navigation: {str(e)}"
                        print(f"   [ERROR] {error_msg}")
                        failed += 1
                        new_failure = pd.DataFrame({
                            'id': [site_id],
                            'url': [url],
                            'reason': [error_msg]
                        })
                        failed_df = pd.concat([failed_df, new_failure], ignore_index=True)
                        failed_df.to_csv(FAILED_URLS_FILE, index=False)
                    
                    except Exception as e:
                        error_msg = f"Erreur de navigation: {str(e)}"
                        print(f"   [ERROR] {error_msg}")
                        failed += 1
                        new_failure = pd.DataFrame({
                            'id': [site_id],
                            'url': [url],
                            'reason': [error_msg]
                        })
                        failed_df = pd.concat([failed_df, new_failure], ignore_index=True)
                        failed_df.to_csv(FAILED_URLS_FILE, index=False)
                    
                    finally:
                        await page.close()
                
                except Exception as e:
                    error_msg = f"Erreur critique: {str(e)}"
                    print(f"   [CRITICAL] {error_msg}")
                    failed += 1
                    new_failure = pd.DataFrame({
                        'id': [site_id],
                        'url': [url],
                        'reason': [error_msg]
                    })
                    failed_df = pd.concat([failed_df, new_failure], ignore_index=True)
                    failed_df.to_csv(FAILED_URLS_FILE, index=False)
            
            await context.close()
            await browser.close()
        
        except Exception as e:
            print(f"[CRITICAL] {e}")
            raise
        
        finally:
            end_time = time.time()
            total_time = end_time - start_time
            hours, remainder = divmod(total_time, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            # Initialiser le dictionnaire des erreurs catégorisées
            categorized_errors = {
                'captcha': 0,
                'timeout': 0,
                'not_found': 0,
                'access_denied': 0,
                'unknown_error': 0
            }
            
            # Rapport final détaillé
            print("\n" + "="*50)
            print(" RAPPORT D'EXÉCUTION FINAL")
            print("="*50)
            
            print("\n Temps d'exécution:")
            print(f"   • Début: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")
            print(f"   • Fin: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))}")
            print(f"   • Durée totale: {int(hours)}h {int(minutes)}m {int(seconds)}s")
            
            print("\n Statistiques de traitement:")
            print(f"   • URLs totales: {total_urls}")
            print(f"   • Succès: {successful} ({(successful/total_urls*100):.1f}%)")
            print(f"   • Échecs: {failed} ({(failed/total_urls*100):.1f}%)")
            
            # Calculer la moyenne de temps par URL
            avg_time_per_url = total_time / total_urls
            print(f"   • Temps moyen par URL: {avg_time_per_url:.1f} secondes")
            
            print("\n Fichiers générés:")
            print(f"   └── {SCREENSHOTS_DIR}/")
            print(f"       ├── full_page/ ({len(list(Path(FULL_PAGE_DIR).glob('*.png')))} fichiers)")
            print(f"       ├── content_page/ ({len(list(Path(CONTENT_DIR).glob('*.png')))} fichiers)")
            print(f"       └── failed_urls.csv")
            
            if failed > 0:
                print("\n Analyse des échecs:")
                # Initialiser le dictionnaire des erreurs catégorisées
                categorized_errors = {
                    'captcha': 0,
                    'timeout': 0,
                    'not_found': 0,
                    'access_denied': 0,
                    'unknown_error': 0
                }
                
                # Compter les erreurs par catégorie
                for error_msg in failed_df['reason']:
                    error_type = categorize_error(str(error_msg))
                    categorized_errors[error_type] += 1
                
                # Afficher les erreurs par catégorie
                for error_type, count in categorized_errors.items():
                    if count > 0:  # N'afficher que les types d'erreurs qui se sont produits
                        percentage = (count/failed*100)
                        print(f"   • {error_type}: {count} ({percentage:.1f}%)")
                    
            # Sauvegarder le rapport dans un fichier
            report_path = SCREENSHOTS_DIR / "rapport_execution.txt"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(f"RAPPORT D'EXÉCUTION - {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"URLs traitées: {total_urls}\n")
                f.write(f"Succès: {successful} ({(successful/total_urls*100):.1f}%)\n")
                f.write(f"Échecs: {failed} ({(failed/total_urls*100):.1f}%)\n")
                f.write(f"Temps total: {int(hours)}h {int(minutes)}m {int(seconds)}s\n")
                
                if failed > 0:
                    f.write("\nDétail des erreurs:\n")
                    for error_type, count in categorized_errors.items():
                        percentage = (count/failed*100)
                        f.write(f"- {error_type}: {count} ({percentage:.1f}%)\n")
            
            print(f"\n Rapport complet sauvegardé dans: rapport_execution.txt")

if __name__ == "__main__":
    print(" Démarrage du traitement...")
    asyncio.run(main())
    print("\n Traitement terminé!")
