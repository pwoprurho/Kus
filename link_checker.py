import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

def find_html_files(start_path):
    html_files = []
    for root, _, files in os.walk(start_path):
        for file in files:
            if file.endswith(".html"):
                html_files.append(os.path.join(root, file))
    return html_files

def check_link(base_url, link):
    if link.startswith("mailto:") or link.startswith("tel:"):
        return True, "Skipping mailto/tel link"
    
    if link.startswith("#"):
        return True, "Skipping anchor link"

    parsed_link = urlparse(link)
    if parsed_link.scheme and parsed_link.netloc:
        # External link
        try:
            response = requests.head(link, allow_redirects=True, timeout=5)
            if response.status_code == 200:
                return True, "External link is OK"
            else:
                return False, f"External link returned status code {response.status_code}"
        except requests.RequestException as e:
            return False, f"External link failed: {e}"
    else:
        # Internal link
        # Construct the absolute path to the linked file
        if link.startswith('/'):
            abs_path = os.path.abspath(os.path.join(os.getcwd(), link.lstrip('/')))
        else:
            abs_path = os.path.abspath(os.path.join(os.path.dirname(base_url), link))

        # Check if the file exists
        if os.path.exists(abs_path):
            return True, "Internal link is OK"
        else:
            # check if it is a route
            if link.startswith('/'):
                return True, "Internal link is a route"
            return False, f"Internal link not found at {abs_path}"


def main():
    html_files = find_html_files("templates")
    broken_links = []

    for html_file in html_files:
        with open(html_file, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                is_valid, message = check_link(html_file, href)
                if not is_valid:
                    broken_links.append((html_file, href, message))

    if broken_links:
        print("Broken links found:")
        for file, link, msg in broken_links:
            print(f"  - In {file}: {link} ({msg})")
    else:
        print("No broken links found!")

if __name__ == "__main__":
    main()
