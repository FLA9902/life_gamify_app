#!/bin/bash
# Create virtual environment and install dependencies

echo "📦 Creating virtual environment..."
python3 -m venv venv

echo "🔧 Activating virtual environment..."
source venv/bin/activate

echo "⬆️ Upgrading pip..."
pip install --upgrade pip

echo "📦 Installing dependencies from requirements.txt..."
pip install --no-cache-dir -r requirements.txt

echo "✅ Setup complete. Run the app using:"
echo "source venv/bin/activate && streamlit run app.py"