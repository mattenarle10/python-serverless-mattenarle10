from flask import Flask, jsonify, request, render_template
import requests
from config import SERVERLESS_API_URL

app = Flask(__name__, static_folder="static", template_folder="templates")

@app.route("/")
def home():
    return render_template("index.html")

@app.route('/products', methods=['GET'])
def get_products():
    response = requests.get(f"{SERVERLESS_API_URL}/products")
    return jsonify(response.json()), response.status_code

@app.route('/products', methods=['POST'])
def create_product():
    product_data = request.json
    response = requests.post(f"{SERVERLESS_API_URL}/products", json=product_data)
    return jsonify(response.json()), response.status_code

@app.route('/products/<product_id>', methods=['GET'])
def get_product(product_id):
    response = requests.get(f"{SERVERLESS_API_URL}/products/{product_id}")
    return jsonify(response.json()), response.status_code

@app.route('/products/<product_id>', methods=['DELETE'])
def delete_product(product_id):
    response = requests.delete(f"{SERVERLESS_API_URL}/products/{product_id}")
    return jsonify(response.json()), response.status_code

@app.route('/products/<product_id>', methods=['PUT'])
def modify_product(product_id):
    product_data = request.json
    response = requests.put(f"{SERVERLESS_API_URL}/products/{product_id}", json=product_data)
    return jsonify(response.json()), response.status_code

@app.route('/inventory', methods=['POST'])
def add_stock_to_product():
    inventory_data = request.json
    response = requests.post(f"{SERVERLESS_API_URL}/inventory", json=inventory_data)
    return jsonify(response.json()), response.status_code

@app.route('/events/inventory-check/setup', methods=['POST'])
def setup_inventory_check():
    data = request.json
    response = requests.post(f"{SERVERLESS_API_URL}/events/inventory-check/setup", json=data)
    return jsonify(response.json()), response.status_code

@app.route('/events/inventory-check', methods=['POST'])
def check_low_inventory():
    data = request.json
    response = requests.post(f"{SERVERLESS_API_URL}/events/inventory-check", json=data)
    return jsonify(response.json()), response.status_code

@app.route('/events/test-trigger', methods=['POST'])
def test_event_trigger():
    data = request.json
    response = requests.post(f"{SERVERLESS_API_URL}/events/test-trigger", json=data)
    return jsonify(response.json()), response.status_code

if __name__ == "__main__":
    app.run(debug=True, port=8080)
