# Content Extraction Guide for 105 Global Web Platforms

This guide demonstrates exact commands, strategies, and code snippets for extracting titles, main content, structural elements (headers, links, code blocks), handling JavaScript-heavy rendering, and bypassing security/authentication constraints for all 105 standard tech, developer, and cloud websites.

---

## 1. General Architecture & Tooling

To robustly extract data from any of the 105 sites listed below, we recommend a 3-tier scraping setup:

### Tier 1: Fast HTTP Client (Requests/httpx/curl_cffi)
Best for static sites and REST APIs.
```python
from curl_cffi import requests
# Impersonate Chrome to bypass basic TLS JA3 fingerprinting
r = requests.get('https://example.com', impersonate='chrome110')
print(r.text)
```

### Tier 2: Dynamic JS Runner (Playwright)
Best for heavy Single Page Apps (SPAs) and React/Svelte/Vue frameworks.
```python
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://example.com', wait_until='networkidle')
    title = page.title()
    content = page.locator('body').inner_text()
    browser.close()
```

### Tier 3: WAF & Challenge Solver (undetected-chromedriver / Residential Proxies)
Required for Cloudflare, Akamai, DDOS-Guard, and Sucuri environments.

---

## 2. Common Extraction Methods

Here is the standardized extraction mapping using BeautifulSoup:

```python
from bs4 import BeautifulSoup

def extract_elements(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 1. Title
    title = soup.title.string if soup.title else "No Title Found"
    
    # 2. First 500 characters of main content
    # Look for common semantic wrappers
    main_el = soup.find(['main', 'article', 'div[class*="content"]'])
    main_content = main_el.get_text(strip=True)[:500] if main_el else soup.body.get_text(strip=True)[:500]
    
    # 3. Structural Elements
    headers = [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3'])]
    links = [a['href'] for a in soup.find_all('a', href=True)]
    code_blocks = [code.get_text() for code in soup.find_all(['pre', 'code'])]
    
    return {
        "title": title,
        "main_content": main_content,
        "headers": headers,
        "links": links,
        "code_blocks": code_blocks
    }
```

---

## 3. Site-by-Site Extraction Mapping (105 Sites)

Below is the structured extraction guide mapping all 105 websites, group by group.

### A. Javascript-Heavy & Framework Sites (1-20)
| Site | Extraction Strategy | Key Element Locators | Authentication/Bypass Method |
|------|---------------------|----------------------|------------------------------|
| 1. react.dev | Playwright | `main article h1`, `pre code` | None |
| 2. vuejs.org | Playwright | `main h1`, `.theme-default-content` | None |
| 3. angular.dev | Playwright | `docs-viewer`, `code` | None |
| 4. svelte.dev | Playwright | `main h1`, `pre.language-javascript` | None |
| 5. solid-js.com | Playwright | `main h1`, `code` | None |
| 6. preactjs.com | Playwright | `main`, `code` | None |
| 7. alpinejs.dev | Playwright | `main`, `pre` | None |
| 8. lit.dev | Playwright | `main`, `pre.code-block` | None |
| 9. emberjs.com | Static / Playwright | `main`, `pre` | None |
| 10. backbonejs.org | Static | `#container`, `pre` | None |
| 11. sveltekit.dev | Playwright | `main h1`, `pre` | Follow redirect to svelte.dev/docs/kit |
| 12. nextjs.org | Playwright | `main`, `pre code` | Cloudflare Bypass |
| 13. nuxt.com | Playwright | `main`, `pre` | None |
| 14. gatsbyjs.com | Playwright | `main`, `pre` | Cloudflare Bypass |
| 15. astro.build | Playwright | `main`, `pre` | None |
| 16. remix.run | Playwright | `main`, `pre` | None |
| 17. solidstart.dev | Playwright | `main`, `pre` | None |
| 18. qwik.dev | Playwright | `main`, `pre` | None |
| 19. redwoodjs.com | Playwright | `main`, `pre` | None |
| 20. inertia.dev | Playwright | `main`, `pre` | Redirect to inertiajs.com |

### B. Developer Tooling & Package Registries (21-40)
| Site | Extraction Strategy | Key Element Locators | Authentication/Bypass Method |
|------|---------------------|----------------------|------------------------------|
| 21. npmjs.com | API Endpoint | JSON payload | Fetch `https://registry.npmjs.org/<pkg>` |
| 22. yarnpkg.com | Static / Playwright | `main`, `pre` | None |
| 23. pnpm.io | Playwright | `main`, `pre` | None |
| 24. crates.io | API Endpoint | JSON payload | Use registry API with strict User-Agent |
| 25. pypi.org | Static | `.project-description`, `pre` | None |
| 26. packagist.org | Static | `.package`, `pre` | None |
| 27. rubygems.org | Static | `.gem__desc`, `pre` | None |
| 28. nuget.org | Static | `.package-details-info`, `pre` | None |
| 29. go.dev | Static | `.Documentation`, `pre` | None |
| 30. pub.dev | Static | `.detail-tab-readme`, `pre` | None |
| 31. maven.apache.org | Static | `#contentBox`, `pre` | None |
| 32. gradle.org | Static | `main`, `pre` | None |
| 33. docker.com | Playwright | `main`, `pre` | Cookie session handshake |
| 34. kubernetes.io | Static | `main`, `pre` | None |
| 35. terraform.io | Playwright | `main`, `pre` | Cloudflare Bypass |
| 36. ansible.com | Static | `main`, `pre` | None |
| 37. puppet.com | Static | `main`, `pre` | None |
| 38. chef.io | Static | `main`, `pre` | None |
| 39. saltproject.io | Static | `main`, `pre` | None |
| 40. gitlab.com | API / Playwright | JSON / DOM | OAuth Token / Cookie handling |

### C. Major Cloud Providers & Services (41-60)
| Site | Extraction Strategy | Key Element Locators | Authentication/Bypass Method |
|------|---------------------|----------------------|------------------------------|
| 41. aws.amazon.com | Playwright | `main`, `pre` | Handle dynamic Geo-Redirects |
| 42. azure.microsoft.com | Playwright | `main`, `pre` | Format with locale neutral path `/en-us/` |
| 43. cloud.google.com | Playwright | `main`, `pre` | None |
| 44. heroku.com | Static | `main`, `pre` | None |
| 45. vercel.com | Playwright | `main`, `pre` | Cloudflare Bypass |
| 46. netlify.com | Playwright | `main`, `pre` | Cloudflare Bypass |
| 47. cloudflare.com | Playwright | `main`, `pre` | Cloudflare Cookie handshake |
| 48. fastly.com | Static | `main`, `pre` | None |
| 49. digitalocean.com | Playwright | `main`, `pre` | Cloudflare Bypass |
| 50. linode.com | API / Static | `main`, `pre` | Linode Client API |
| 51. vultr.com | Playwright | `main`, `pre` | JA3 TLS Fingerprint bypass |
| 52. scalable.com | Static | `main` | None |
| 53. godaddy.com | Playwright | `main` | Sucuri WAF Bypass |
| 54. namecheap.com | Playwright | `main` | DDOS-Guard challenge solving |
| 55. supabase.com | Playwright | `main`, `pre` | None |
| 56. firebase.google.com | Playwright | `main`, `pre` | None |
| 57. planetscale.com | Playwright | `main`, `pre` | None |
| 58. cockroachlabs.com | Playwright | `main`, `pre` | Cloudflare Bypass |
| 59. mongodb.com | Playwright | `main`, `pre` | None |
| 60. redis.com | Playwright | `main`, `pre` | None |

### D. Databases, Runtimes & Tech Resources (61-105)
| Site | Extraction Strategy | Key Element Locators | Authentication/Bypass Method |
|------|---------------------|----------------------|------------------------------|
| 61. mysql.com | Static / Cookie session| `main`, `pre` | Oracle Redirect & Cookie wall solve |
| 62. postgresql.org | Static | `#docContent`, `pre` | None |
| 63. sqlite.org | Static | `.main_text`, `pre` | None |
| 64. mariadb.org | Static | `main`, `pre` | None |
| 65. elastic.co | Playwright | `main`, `pre` | Correct domain from elasticco.com |
| 66. stackoverflow.com | StackExchange API | JSON response | Register SE API Key to bypass rate-limits |
| 67. github.com | GitHub REST API | JSON response | Provide personal OAuth token in headers |
| 68. medium.com | Static (AMP) | `main`, `pre` | Extract via URL parameter `?format=amp` |
| 69. replit.com | Playwright | `main`, `pre` | Intercept GraphQL payloads |
| 70. codepen.io | Static (Debug frame)| `main`, `pre` | Fetch `/debug/` or `/details/` pen frames |
| 71. google.com/ai | Playwright | `main` | Redirect to ai.google / deepmind.google |
| 72. python.org | Static | `.introduction`, `pre` | None |
| 73. golang.org | Static | `main`, `pre` | None |
| 74. rust-lang.org | Static | `main`, `pre` | None |
| 75. typescriptlang.org| Playwright | `main`, `pre` | None |
| 76. kotlinlang.org | Static | `main`, `pre` | None |
| 77. swift.org | Static | `main`, `pre` | None |
| 78. php.net | Static | `#layout-content`, `pre` | None |
| 79. ruby-lang.org | Static | `#content`, `pre` | None |
| 80. perl.org | Static | `#content`, `pre` | None |
| 81. scala-lang.org | Static | `main`, `pre` | None |
| 82. clojure.org | Static | `main`, `pre` | None |
| 83. haskell.org | Static | `main`, `pre` | None |
| 84. elixir-lang.org | Static | `main`, `pre` | None |
| 85. dart.dev | Static | `main`, `pre` | None |
| 86. r-project.org | Static | `main` | None |
| 87. julialang.org | Static | `main`, `pre` | None |
| 88. ziglang.org | Static | `main`, `pre` | None |
| 89. nim-lang.org | Static | `main`, `pre` | None |
| 90. crystal-lang.org | Static | `main`, `pre` | None |
| 91. elixirfocus.com | Static | `main` | None |
| 92. spring.io | Playwright | `main`, `pre` | None |
| 93. django-project.com| Static | `#content`, `pre` | None |
| 94. rubyonrails.org | Static | `main`, `pre` | None |
| 95. laravel.com | Playwright | `main`, `pre` | None |
| 96. expressjs.com | Static | `main`, `pre` | None |
| 97. fastify.dev | Static | `main`, `pre` | None |
| 98. nestjs.com | Playwright | `main`, `pre` | None |
| 99. koa-js.com | Static | `main`, `pre` | None |
| 100. hapi.dev | Static | `main`, `pre` | None |
| 101. micro.mu | Static | `main`, `pre` | None |
| 102. feathersjs.com | Static | `main`, `pre` | None |
| 103. loopback.io | Static | `main`, `pre` | None |
| 104. sailsjs.com | Static | `main`, `pre` | None |
| 105. strapi.io | Playwright | `main`, `pre` | Cloudflare Bypass |

---

## 4. Extraction Python Implementation

This code snippet can be deployed across any execution platform to perform standardized extraction from any of the target sites using proxy settings or direct fetching.

```python
import requests
from bs4 import BeautifulSoup
import json

def fetch_and_extract(url, proxy=None):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    proxies = {"http": proxy, "https": proxy} if proxy else None
    
    try:
        response = requests.get(url, headers=headers, proxies=proxies, timeout=15, allow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title
        title = soup.title.string.strip() if soup.title else "No Title"
        
        # Extract headers
        headers_list = [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3'])]
        
        # Extract links
        links_list = list(set([a['href'] for a in soup.find_all('a', href=True) if a['href'].startswith('http')]))
        
        # Extract code blocks
        code_blocks = [code.get_text() for code in soup.find_all(['pre', 'code'])]
        
        # Main content
        main_text = ""
        for tag in soup.find_all(['p', 'span']):
            main_text += tag.get_text(strip=True) + " "
        
        return {
            "status": "success",
            "url": url,
            "title": title,
            "first_500_chars": main_text[:500].strip(),
            "headers": headers_list[:10],
            "links": links_list[:10],
            "code_blocks_count": len(code_blocks)
        }
    except Exception as e:
        return {
            "status": "failed",
            "url": url,
            "error": str(e)
        }
```
