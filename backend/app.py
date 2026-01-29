from flask import Flask, request, jsonify
from core import MaterialAbs
import xraylib as xrl
import json
import logging

import os

# Serve static files from the React app build folder
app = Flask(__name__, static_folder="../frontend/dist", static_url_path="/")
logging.basicConfig(level=logging.INFO)

SHELL_MAP = {
    "K": xrl.K_SHELL,
    "L1": xrl.L1_SHELL,
    "L2": xrl.L2_SHELL,
    "L3": xrl.L3_SHELL
}

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/calculate', methods=['POST'])
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

@app.route('/elements', methods=['GET'])
def get_elements():
    elements = []
    for Z in range(1, 101):
        try:
             sym = xrl.AtomicNumberToSymbol(Z)
             elements.append({"symbol": sym, "atomic_number": Z})
        except:
            pass
    return jsonify(elements)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)
