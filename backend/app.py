from flask import Flask, request, jsonify
from core import MaterialAbs
import xraylib as xrl
import json
import logging

import os
try:
    from flask_cors import CORS
except ImportError:
    CORS = None

# Serve static files from the React app build folder
app = Flask(__name__, static_folder="../frontend/dist", static_url_path="/")
if CORS:
    CORS(app)
logging.basicConfig(level=logging.INFO)

# --- Likes Storage ---
LIKES_FILE = os.path.join(os.path.dirname(__file__), 'likes.json')

def get_likes_count():
    """Read the current likes count from file."""
    try:
        if os.path.exists(LIKES_FILE):
            with open(LIKES_FILE, 'r') as f:
                data = json.load(f)
                return data.get('count', 0)
    except Exception as e:
        logging.error(f"Error reading likes: {e}")
    return 0

def save_likes_count(count):
    """Save the likes count to file."""
    try:
        with open(LIKES_FILE, 'w') as f:
            json.dump({'count': max(0, count)}, f)
        return True
    except Exception as e:
        logging.error(f"Error saving likes: {e}")
        return False

SHELL_MAP = {
    "K": xrl.K_SHELL,
    "L1": xrl.L1_SHELL,
    "L2": xrl.L2_SHELL,
    "L3": xrl.L3_SHELL
}

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/calculate', methods=['POST'])
def calculate():
    try:
        data = request.json
        compounds = data.get('compounds', [])
        edges = data.get('edges', [])
        
        results = []
        
        for edge_cfg in edges:
            element = edge_cfg.get('element')
            edge_type = edge_cfg.get('edge_type')
            
            try:
                # MaterialAbs expects [{'compound': str, 'area_density': float}]
                mat = MaterialAbs(compounds, element, edge_type)
                mat.abs_calc()
                
                # Generate plot figure
                fig = mat.plot(abs_edge=f'{mat.element} {mat.edge}')
                
                # Convert to JSON
                plot_json = json.loads(fig.to_json())
                
                results.append({
                    "element": element,
                    "edge": edge_type,
                    "plot": plot_json,
                    "edge_jump": getattr(mat, 'edge_jump', 0),
                    "abs_max": getattr(mat, 'abs_max', 0),
                    "edge_value": getattr(mat, 'edge_value', 0),
                    "compound_latex": getattr(mat, 'compound_name_all_latex', "")
                })
            except Exception as e:
                logging.error(f"Error calculating {element} {edge_type}: {e}")
                results.append({
                    "element": element,
                    "edge": edge_type,
                    "error": str(e)
                })

        return jsonify({"results": results})

    except Exception as e:
        logging.error(f"Global error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/elements', methods=['GET'])
def get_elements():
    elements = []
    for Z in range(1, 101):
        try:
             sym = xrl.AtomicNumberToSymbol(Z)
             elements.append({"symbol": sym, "atomic_number": Z})
        except:
            pass
    return jsonify(elements)

@app.route('/api/likes', methods=['GET'])
def get_likes():
    """Get the current likes count."""
    return jsonify({"count": get_likes_count()})

@app.route('/api/likes', methods=['POST'])
def update_likes():
    """Update the likes count (increment or decrement)."""
    try:
        data = request.json or {}
        action = data.get('action', 'like')  # 'like' or 'unlike'
        
        current_count = get_likes_count()
        
        if action == 'like':
            new_count = current_count + 1
        elif action == 'unlike':
            new_count = max(0, current_count - 1)
        else:
            return jsonify({"error": "Invalid action"}), 400
        
        save_likes_count(new_count)
        return jsonify({"count": new_count})
    except Exception as e:
        logging.error(f"Error updating likes: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)

