# cloudflare-worker-local-runner
A personal project to run multiple Cloudflare Wrangler dev sessions locally.

## Do I Need This?
Probably not. In most cases, you don't need this. This project happened because I was struggling with local development in Windows 11 for Cloudflare Worker Wrangler. I had to run `npx wrangler dev` in multiple terminals (I have over 10 terminals to manage and monitor), so this project was created to simplify that process.

### Node.js Behavior
It took me about 2 hours to discover that **Node.js** does not shut down if you just close the terminal. You can kill its process, but an easier way is to make a small HTTP request to it. It will realize that no one is there anymore and will shut down itself.

Requirements
* Python 3.12
* pip
* Python Packages

Install the required packages with:
```pip install PyQt5 qasync aiohttp```
