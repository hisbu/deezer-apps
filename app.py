from flask import Flask, render_template, request, jsonify
import requests
import json
from datetime import datetime

app = Flask(__name__)

# Konfigurasi API Deezer
DEEZER_BASE_URL = "https://api.deezer.com"

# Custom template filters
@app.template_filter('format_number')
def format_number(value):
    """Format large numbers with commas"""
    if value is None:
        return "0"
    try:
        return "{:,}".format(int(value))
    except (ValueError, TypeError):
        return str(value)

@app.template_filter('format_duration')
def format_duration(seconds):
    """Format duration from seconds to MM:SS"""
    if seconds is None:
        return "0:00"
    try:
        minutes = int(seconds) // 60
        seconds = int(seconds) % 60
        return f"{minutes}:{seconds:02d}"
    except (ValueError, TypeError):
        return "0:00"

def make_api_request(endpoint):
    """Fungsi untuk melakukan request ke API Deezer dengan error handling"""
    try:
        # Bersihkan endpoint dari karakter tidak valid
        endpoint = endpoint.strip().lstrip('/')
        url = f"{DEEZER_BASE_URL}/{endpoint}"
        
        print(f"🌐 Making request to: {url}")
        
        # Gunakan timeout yang reasonable
        response = requests.get(url, timeout=15)
        
        print(f"📡 Response status: {response.status_code}")
        
        # Cek status code
        if response.status_code != 200:
            print(f"🚫 HTTP Error {response.status_code}")
            return None
        
        # Parse JSON
        data = response.json()
        
        # Cek jika response adalah error dari Deezer
        if isinstance(data, dict) and 'error' in data:
            print(f"❌ Deezer API Error: {data['error']}")
            return None
            
        print(f"✅ API Request successful")
        return data
        
    except requests.exceptions.Timeout:
        print(f"⏰ Timeout error: Request took too long")
        return None
    except requests.exceptions.ConnectionError:
        print(f"🔌 Connection error: Cannot connect to Deezer API")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"🚫 HTTP error: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"📄 JSON decode error: {e}")
        print(f"📄 Response text: {response.text[:200] if 'response' in locals() else 'No response'}")
        return None
    except Exception as e:
        print(f"🔥 Unexpected error in make_api_request: {e}")
        return None


@app.route('/')
def index():
    """Halaman utama dengan chart dan editorial content"""
    # Ambil data chart
    chart_data = make_api_request("chart/0")
    
    # Ambil data editorial
    editorial_data = make_api_request("editorial")
    
    return render_template('index.html', 
                         chart_data=chart_data, 
                         editorial_data=editorial_data)

@app.route('/search')
def search():
    """Halaman pencarian"""
    try:
        query = request.args.get('q', '')
        search_type = request.args.get('type', 'track')
        results = None
        
        print(f"🔍 Search endpoint called - Query: '{query}', Type: '{search_type}'")
        
        if query:
            print(f"🔍 Searching for: '{query}' (type: {search_type})")
            
            # Encode query untuk URL
            encoded_query = requests.utils.quote(query)
            api_url = f"search/{search_type}?q={encoded_query}&limit=10"  # Kurangi limit untuk testing
            
            print(f"📡 API URL: {DEEZER_BASE_URL}/{api_url}")
            
            start_time = datetime.now()
            results = make_api_request(api_url)
            end_time = datetime.now()
            
            # Debug search results
            if results is not None:
                response_time = (end_time - start_time).total_seconds()
                print(f"✅ Search completed in {response_time:.2f}s")
                
                if isinstance(results, dict):
                    print(f"📊 Results keys: {list(results.keys())}")
                    if 'data' in results:
                        print(f"📊 Results count: {len(results.get('data', []))} items")
                    else:
                        print("❌ No 'data' key in results")
                else:
                    print(f"❓ Unexpected results type: {type(results)}")
            else:
                print("❌ No search results received from API")
        
        return render_template('search.html', 
                             results=results, 
                             query=query, 
                             search_type=search_type)
                             
    except Exception as e:
        print(f"🔥 ERROR in search function: {str(e)}")
        print(f"🔥 Error type: {type(e).__name__}")
        import traceback
        print(f"🔥 Traceback: {traceback.format_exc()}")
        
        # Return error page atau fallback
        return render_template('search.html', 
                             results=None, 
                             query=request.args.get('q', ''),
                             search_type=request.args.get('type', 'track'),
                             error=str(e))



@app.route('/user/<user_id>')
def user_detail(user_id):
    """Detail pengguna"""
    user_data = make_api_request(f"user/{user_id}")
    return render_template('detail.html', 
                         data=user_data, 
                         title=f"User {user_id}",
                         type="user")


@app.route('/track/<track_id>')
def track_detail(track_id):
    """Detail track"""
    print(f"Fetching track details for ID: {track_id}")  # Debug line
    track_data = make_api_request(f"track/{track_id}")
    
    # Debug: Print response untuk troubleshooting
    if track_data:
        print(f"Track data received: {track_data.get('title', 'No title')}")
        # Debug lebih detail
        print(f"Track keys: {track_data.keys()}")
        if 'error' in track_data:
            print(f"API Error: {track_data['error']}")
    else:
        print("No track data received from API")
    
    return render_template('detail.html', 
                         data=track_data, 
                         title="Track Details",
                         type="track")

@app.route('/editorial')
def editorial_list():
    """Daftar editorial"""
    editorial_data = make_api_request("editorial")
    
    # Debug editorial data
    if editorial_data:
        print(f"Editorial data received: {len(editorial_data.get('data', []))} editorials")
    else:
        print("No editorial data received")
    
    return render_template('detail.html', 
                         data=editorial_data,
                         title="Editorial Picks",
                         type="editorial")

@app.route('/editorial/<editorial_id>')
def editorial_detail(editorial_id):
    """Detail editorial"""
    print(f"Fetching editorial details for ID: {editorial_id}")
    
    # Untuk editorial, kita perlu mengambil daftar tracks/playlists dari editorial tersebut
    # Deezer API tidak memiliki endpoint khusus untuk single editorial, jadi kita gunakan selection
    editorial_data = make_api_request(f"editorial/{editorial_id}/selection")
    
    if editorial_data:
        print(f"Editorial selection received: {len(editorial_data.get('data', []))} items")
    else:
        print("No editorial selection received")
    
    return render_template('detail.html', 
                         data=editorial_data,
                         title="Editorial Selection",
                         type="editorial_detail",
                         editorial_id=editorial_id)


@app.route('/album/<album_id>')
def album_detail(album_id):
    """Detail album"""
    album_data = make_api_request(f"album/{album_id}")
    return render_template('detail.html', 
                         data=album_data, 
                         title="Album Details",
                         type="album")


@app.route('/artist/<artist_id>')
def artist_detail(artist_id):
    """Detail artist"""
    artist_data = make_api_request(f"artist/{artist_id}")
    # Ambil top tracks artist
    top_tracks = make_api_request(f"artist/{artist_id}/top?limit=10")
    return render_template('detail.html', 
                         data=artist_data, 
                         top_tracks=top_tracks,
                         title="Artist Details",
                         type="artist")

@app.route('/playlist/<playlist_id>')
def playlist_detail(playlist_id):
    """Detail playlist"""
    playlist_data = make_api_request(f"playlist/{playlist_id}")
    return render_template('detail.html', 
                         data=playlist_data, 
                         title="Playlist Details",
                         type="playlist")

@app.route('/genre')
def genre_list():
    """Daftar genre"""
    genre_data = make_api_request("genre")
    
    # Debug genre data
    if genre_data:
        print(f"Genre data received: {len(genre_data.get('data', []))} genres")
    else:
        print("No genre data received")
    
    return render_template('detail.html', 
                         data=genre_data,
                         title="Music Genres",
                         type="genre")


@app.route('/radio')
def radio_list():
    """Daftar radio"""
    radio_data = make_api_request("radio")
    
    # Debug radio data
    if radio_data:
        print(f"Radio data received: {len(radio_data.get('data', []))} stations")
    else:
        print("No radio data received")
    
    return render_template('detail.html', 
                         data=radio_data,
                         title="Radio Stations", 
                         type="radio")


@app.route('/episode/<episode_id>')
def episode_detail(episode_id):
    """Detail episode"""
    episode_data = make_api_request(f"episode/{episode_id}")
    return render_template('detail.html', 
                         data=episode_data, 
                         title="Episode Details",
                         type="episode")

# Error handler
@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error=error), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error=error), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5006)

#d
