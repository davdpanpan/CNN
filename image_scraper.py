import bs4
import requests
import os
import time
import io
import base64

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from PIL import Image
from bs4 import *

options = Options()
driver = webdriver.Chrome(options=options)

def download_image(download_path, url, file_name):
    try:
        image_content = requests.get(url).content
        image_file = io.BytesIO(image_content)
        image = Image.open(image_file)
        file_path = download_path + file_name
    
        with open(file_path, 'wb') as f:
            image.save(f, 'JPEG')
        print('success')
    except Exception as e:
        print('failed -', e)


def scrape_google_images(query, num_images, output_directory):
    # Create output directory if it doesn't exist
    os.makedirs(output_directory, exist_ok=True)
    
    # Setting up Chrome webdriver
    driver = webdriver.Chrome(options=options)

    try:
        # Open Google Images
        driver.get('https://www.google.com/imghp?hl=en')

        # Find the search bar and input the query
        search_bar = driver.find_element(By.NAME, 'q')
        search_bar.send_keys(query)
        search_bar.submit()

        # Wait for results to load
        time.sleep(3)

        # Scroll to load more images
        scroll_pause_time = 2
        last_height = driver.execute_script("return document.body.scrollHeight")

        scroll_attempts = 0
        max_scroll_attempts = 10  # Add maximum scroll attempts

        while len(driver.find_elements(By.CSS_SELECTOR, 'img[data-src], img[src]')) < num_images and scroll_attempts < max_scroll_attempts:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)  # Increase wait time
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                scroll_attempts += 1  # Count consecutive failed scrolls
            else:
                scroll_attempts = 0  # Reset if new content loaded
            last_height = new_height

        # Get page source and parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Find all image elements (look for both src and data-src)
        img_elements = soup.find_all('img')
        
        downloaded_count = 0
        
        # Download and save images
        for i, img in enumerate(img_elements):
            if downloaded_count >= num_images:
                break
                
            try:
                # Try to get image URL from src or data-src
                img_url = img.get('src') or img.get('data-src')
                
                if not img_url:
                    continue
                    
                # Skip very small images or icons
                if 'data:image' in img_url and len(img_url) < 1000:
                    continue
                
                image_name = f"{query.replace(" ", "_")}_{downloaded_count}.jpg"
                image_path = os.path.join(output_directory, image_name)
                
                if img_url.startswith('data:image/'):
                    # Handle base64 encoded images
                    try:
                        # Extract base64 data after the comma
                        base64_data = img_url.split(',')[1]
                        imgdata = base64.b64decode(base64_data)
                        with open(image_path, 'wb') as f:
                            f.write(imgdata)
                        print(f"Downloaded {image_name} (base64)")
                        downloaded_count += 1
                    except Exception as e:
                        print(f"Error with base64 image {image_name}: {str(e)}")
                        
                elif img_url.startswith('http'):
                    # Handle regular URLs
                    try:
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                        }
                        response = requests.get(img_url, headers=headers, timeout=10)
                        if response.status_code == 200 and len(response.content) > 1000:
                            with open(image_path, 'wb') as f:
                                f.write(response.content)
                            print(f"Downloaded {image_name}")
                            downloaded_count += 1
                        else:
                            print(f"Failed to download {image_name}. Status: {response.status_code}")
                    except Exception as e:
                        print(f"Error downloading {image_name}: {str(e)}")
                        
            except Exception as e:
                print(f"Error processing image {i}: {str(e)}")

        print(f"Total images downloaded: {downloaded_count}")
        
    finally:
        # Close the webdriver
        driver.quit()


def clean_dataset(data_dir):
    """
    Remove corrupted or invalid image files from the dataset.
    """
    valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')
    removed_count = 0
    
    for category in os.listdir(data_dir):
        category_path = os.path.join(data_dir, category)
        if not os.path.isdir(category_path):
            continue
            
        print(f"Cleaning {category}...")
        
        for filename in os.listdir(category_path):
            file_path = os.path.join(category_path, filename)
            
            # Skip if not a file
            if not os.path.isfile(file_path):
                continue
                
            # Check file extension
            if not filename.lower().endswith(valid_extensions):
                print(f"Removing {filename} - invalid extension")
                os.remove(file_path)
                removed_count += 1
                continue
            
            # Try to open and verify the image
            try:
                with Image.open(file_path) as img:
                    img.verify()  # Verify the image is valid
            except Exception as e:
                print(f"Removing {filename} - corrupted: {str(e)}")
                os.remove(file_path)
                removed_count += 1
    
    print(f"Removed {removed_count} corrupted/invalid files")