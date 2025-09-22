#!/bin/bash

# Build Tailwind CSS for production
echo "🎨 Building Tailwind CSS..."

# Check if node_modules exists, if not install dependencies
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Build CSS for production
echo "🔨 Compiling CSS..."
npx tailwindcss -i ./static/css/tailwind.css -o ./static/css/compiled.css --minify

echo "✅ CSS build complete!"
echo "📁 Output: static/css/compiled.css"
