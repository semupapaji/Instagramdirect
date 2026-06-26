"""
Instagram Downloader API - Single File Version
Deploy on Vercel with @vercel/python
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import sys
import os
from urllib.parse import urlparse

# ============================================
# Initialize Flask App
# ============================================
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# ============================================
# Instagram Scraper Function
# ============================================

def download_instagram_sync(url):
    """
    Download Instagram content using snapsave.app
    """
    try:
        # Headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
            'content-type': 'application/x-www-form-urlencoded',
            'referer': 'https://snapsave.app/',
            'origin': 'https://snapsave.app',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.5',
            'accept-encoding': 'gzip, deflate, br',
            'connection': 'keep-alive',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'cache-control': 'max-age=0',
            'upgrade-insecure-requests': '1'
        }
        
        # Data to send
        data = {'url': url}
        
        # Send POST request to snapsave
        response = requests.post(
            'https://snapsave.app/action.php?lang=vn',
            data=data,
            headers=headers,
            timeout=30
        )
        
        # Check response status
        if response.status_code != 200:
            return {
                'status': False,
                'msg': f'HTTP Error: {response.status_code}'
            }
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # ============================================
        # METHOD 1: Find .download-items class
        # ============================================
        download_items = soup.find_all('div', class_='download-items')
        
        if download_items:
            for item in download_items:
                # Get quality/resolution
                quality_elem = item.find('div', class_='download-items__meta')
                if not quality_elem:
                    quality_elem = item.find('td')
                
                quality = quality_elem.text.strip() if quality_elem else 'Unknown'
                
                # Get download URL
                btn = item.find('div', class_='download-items__btn')
                if btn:
                    link = btn.find('a')
                    if link and link.get('href'):
                        download_url = link.get('href')
                        
                        # Make URL absolute
                        if not download_url.startswith('http'):
                            download_url = 'https://snapsave.app' + download_url
                        
                        # Get thumbnail
                        thumb_elem = item.find('img')
                        thumbnail = thumb_elem.get('src') if thumb_elem else None
                        
                        # Get media type
                        media_type = 'video' if 'video' in str(item).lower() else 'image'
                        
                        results.append({
                            'quality': quality,
                            'url': download_url,
                            'thumbnail': thumbnail,
                            'type': media_type
                        })
        
        # ============================================
        # METHOD 2: Fallback - .download-box class
        # ============================================
        if not results:
            download_boxes = soup.find_all('div', class_='download-box')
            
            for box in download_boxes:
                link = box.find('a')
                if link and link.get('href'):
                    download_url = link.get('href')
                    
                    if not download_url.startswith('http'):
                        download_url = 'https://snapsave.app' + download_url
                    
                    # Try to get quality
                    quality_elem = box.find('span', class_='quality')
                    quality = quality_elem.text.strip() if quality_elem else 'Download'
                    
                    # Get thumbnail
                    thumb_elem = box.find('img')
                    thumbnail = thumb_elem.get('src') if thumb_elem else None
                    
                    results.append({
                        'quality': quality,
                        'url': download_url,
                        'thumbnail': thumbnail,
                        'type': 'unknown'
                    })
        
        # ============================================
        # METHOD 3: Fallback - Search all tables
        # ============================================
        if not results:
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        # First column = quality
                        quality = cols[0].text.strip()
                        
                        # Second column = download link
                        link = cols[1].find('a')
                        if link and link.get('href'):
                            download_url = link.get('href')
                            
                            if not download_url.startswith('http'):
                                download_url = 'https://snapsave.app' + download_url
                            
                            results.append({
                                'quality': quality or 'Unknown',
                                'url': download_url,
                                'thumbnail': None,
                                'type': 'unknown'
                            })
        
        # ============================================
        # METHOD 4: Direct link search
        # ============================================
        if not results:
            # Search for any download links
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href', '')
                if 'download' in href.lower() or 'get' in href.lower() or 'file' in href.lower():
                    if not href.startswith('http'):
                        href = 'https://snapsave.app' + href
                    
                    results.append({
                        'quality': 'Download',
                        'url': href,
                        'thumbnail': None,
                        'type': 'unknown'
                    })
        
        # Remove duplicates
        seen_urls = set()
        unique_results = []
        for item in results:
            if item['url'] not in seen_urls:
                seen_urls.add(item['url'])
                unique_results.append(item)
        
        # Check if any results found
        if not unique_results:
            return {
                'status': False,
                'msg': 'No media found in this Instagram post. Make sure the post is public.'
            }
        
        return {
            'status': True,
            'data': unique_results,
            'total': len(unique_results)
        }
        
    except requests.exceptions.Timeout:
        return {
            'status': False,
            'msg': 'Request timeout - The server took too long to respond'
        }
    except requests.exceptions.ConnectionError:
        return {
            'status': False,
            'msg': 'Connection error - Failed to connect to the download service'
        }
    except Exception as e:
        print(f"Error in scraper: {str(e)}")
        return {
            'status': False,
            'msg': f'Error: {str(e)}'
        }

# ============================================
# API Routes
# ============================================

@app.route('/', methods=['GET'])
def home():
    """Root endpoint - API Information"""
    return jsonify({
        "name": "Instagram Downloader API",
        "version": "1.0.0",
        "description": "Download Instagram videos, reels, and photos",
        "endpoints": {
            "/": "API Information",
            "/api/health": "Health check",
            "/api/igdl?url=INSTAGRAM_URL": "Download Instagram content"
        },
        "example": "/api/igdl?url=https://www.instagram.com/p/DLHQfPiyucu/",
        "status": "online"
    })

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint for Vercel"""
    return jsonify({
        "status": "healthy",
        "service": "Instagram Downloader",
        "version": "1.0.0",
        "python_version": sys.version.split()[0] if sys.version else "3.9"
    })

@app.route('/api/igdl', methods=['GET'])
def igdl():
    """Main download endpoint"""
    try:
        # Get URL parameter
        url = request.args.get('url')
        
        # Validate URL
        if not url:
            return jsonify({
                "error": "URL parameter is missing",
                "example": "/api/igdl?url=https://www.instagram.com/p/ABC123/"
            }), 400
        
        # Validate Instagram URL
        instagram_pattern = r'^https?:\/\/(www\.)?instagram\.com\/(p|reel|tv|stories)\/[A-Za-z0-9_-]+\/?'
        if not re.match(instagram_pattern, url):
            return jsonify({
                "error": "Invalid Instagram URL",
                "message": "URL must be a valid Instagram post, reel, or story",
                "example": "https://www.instagram.com/p/ABC123/"
            }), 400
        
        # Download Instagram content
        result = download_instagram_sync(url)
        
        # Check if download was successful
        if not result.get('status', False):
            return jsonify({
                "success": False,
                "error": "Download failed",
                "message": result.get('msg', 'Unknown error occurred'),
                "hint": "Make sure the post is public and accessible"
            }), 404
        
        # Return success response
        return jsonify({
            "success": True,
            "data": result.get('data', []),
            "count": result.get('total', len(result.get('data', [])))
        })
        
    except Exception as e:
        print(f"Error in /api/igdl: {str(e)}")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e),
            "hint": "Please try again later"
        }), 500

# ============================================
# Error Handlers
# ============================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Not Found",
        "message": "The requested endpoint does not exist"
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "error": "Method Not Allowed",
        "message": "Only GET requests are supported"
    }), 405

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Internal Server Error",
        "message": "Something went wrong on the server"
    }), 500

# ============================================
# Vercel Serverless Handler
# ============================================

def handler(request, context):
    """
    Vercel serverless function entry point
    Vercel automatically calls this function
    """
    return app(request, context)

# ============================================
# Local Development
# ============================================

if __name__ == '__main__':
    app.run(debug=True, port=5000)
    print("🚀 Server running at http://localhost:5000")