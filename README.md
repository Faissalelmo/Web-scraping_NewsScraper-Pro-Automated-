# 🕷️ Web Scraper Project - `Web_scraper_main2.ipynb`
**Automated News Collection & Analysis System**

![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)
## 📌 Project Overview

This project is a **web scraping notebook** developed in Python, designed to extract data from news websites or blogs. The goal is to collect articles or structured content and output the information in a usable format such as Markdown, JSON, or CSV.

The code utilizes various Python libraries to send HTTP requests, parse HTML pages, extract specific elements, and format the output for downstream tasks (like feeding it to workflows in automation platforms like n8n).

---
## 📊 Architecture Diagram

image: "/Architecture Diagram.png"

## 🛠️ Features

- Scrapes articles and structured content from a target URL (like [telquel.ma](https://telquel.ma))
- Parses and cleans extracted HTML content
- Converts extracted links into structured Markdown format
- Easy to adapt for different domains or websites
- Compatible with automation tools like **n8n**

---

## 📁 File Structure

```
📦 Web Scraper Project
├── Web_scraper_main2.ipynb       # Main Jupyter notebook containing scraping logic
├── output/                       # Folder to save extracted results (if used)
└── README.md                     # Project description and usage instructions
```

---

## 📦 Dependencies

Make sure the following libraries are installed:

```bash
pip install requests beautifulsoup4 pandas markdownify
```

---

## ▶️ How to Run

1. Open the Jupyter notebook: `Web_scraper_main2.ipynb`
2. Set the target URL in the appropriate code cell (e.g. `https://telquel.ma/`)
3. Run the notebook cells step-by-step:
   - Fetch the HTML
   - Parse with BeautifulSoup
   - Extract relevant tags (e.g. `a`, `article`, `h1`, etc.)
   - Format as Markdown or structured JSON
4. Save or export the results

---

## 🧩 Example Output

Sample extracted Markdown structure:

```markdown
- [Accueil](https://telquel.ma/)
- [Qitab](https://telquel.ma/categorie/culture/livres/qitab)
- [Archives](https://telquel.ma/sommaire)
```

---

## 🔄 Integration with n8n

You can pass the Markdown or JSON result to **n8n** using:

- HTTP POST/GET
- Webhook nodes
- File write nodes for markdown

This makes the scraper part of a full automation pipeline.

---

## 📌 Notes

- Always respect the website's `robots.txt` rules
- Add headers to mimic browser user agents to avoid blocks
- You can add delays or use proxies to scrape large datasets

---

## 📃 License

This project is licensed under the MIT License.

---

## 🤝 Contributions

Feel free to fork this repository and propose improvements via pull requests.

---

## 📧 Contact

For questions or issues, contact the author via GitHub or email.

---

Happy scraping! 🕸️

