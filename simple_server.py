#!/usr/bin/env python3
"""
Farm Intel - Simple Production Server
Minimal code, maximum functionality
"""

from flask import Flask, render_template, request
import tensorflow as tf
import numpy as np
import cv2
import os
import pandas as pd
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

app = Flask(__name__)

# Load models
model = None
classes = []
climate_model = None
climate_insights = {}

def load_models():
    global model, classes, climate_model, climate_insights
    
    # Load CNN model
    try:
        model = tf.keras.models.load_model("model/crop_disease_model.h5")
        print("✅ Model loaded")
    except:
        print("❌ Model not found")
        model = None
    
    # Load classes
    try:
        train_datagen = ImageDataGenerator(rescale=1./255)
        train_data = train_datagen.flow_from_directory('dataset/train', target_size=(128,128), batch_size=32, class_mode='categorical')
        classes = list(train_data.class_indices.keys())
        print(f"✅ {len(classes)} classes loaded")
    except:
        classes = ["Unknown"]
    
    # Load climate data
    try:
        climate_data = pd.read_excel("climate_data.xlsx")
        X = climate_data[['temperature_C', 'humidity_%', 'rainfall_mm', 'soil_moisture_%']]
        y = climate_data['crop_disease_status']
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        climate_model = RandomForestClassifier(n_estimators=100, random_state=42)
        climate_model.fit(X_train, y_train)
        
        climate_insights = {
            'accuracy': f"{climate_model.score(X_test, y_test):.1f}",
            'total_samples': len(climate_data),
            'disease_distribution': climate_data['crop_disease_status'].value_counts().to_dict(),
            'avg_conditions': {
                'temperature': f"{climate_data['temperature_C'].mean():.1f}°C",
                'humidity': f"{climate_data['humidity_%'].mean():.1f}%",
                'rainfall': f"{climate_data['rainfall_mm'].mean():.1f}mm",
                'soil_moisture': f"{climate_data['soil_moisture_%'].mean():.1f}%"
            }
        }
        print("✅ Climate data loaded")
    except:
        climate_insights = {'accuracy': 'N/A', 'total_samples': 0, 'disease_distribution': {}, 'avg_conditions': {}}

def predict_image(path):
    if not model:
        return {"error": "Model not available"}
    
    try:
        img = cv2.imread(path)
        if img is None:
            return {"error": "Cannot read image"}
        
        img = cv2.resize(img, (128, 128))
        img = img / 255.0
        img = np.reshape(img, [1, 128, 128, 3])
        
        predictions = model.predict(img, verbose=0)[0]
        confidence = np.max(predictions)
        
        if confidence < 0.4:
            return {"error": "Low confidence"}
        
        index = np.argmax(predictions)
        if index < len(classes):
            return {"disease": classes[index], "confidence": f"{confidence:.1%}"}
        else:
            return {"error": "Prediction error"}
    except:
        return {"error": "Prediction failed"}

# Load models at startup
load_models()

@app.route('/')
def home():
    return render_template('simple.html', prediction=None, prediction_data=None, image_filename=None, climate_insights=climate_insights)

@app.route('/predict', methods=['POST'])
def predict():
    if request.method == 'POST' and 'image' in request.files:
        file = request.files['image']
        if file.filename:
            if not os.path.exists("static"):
                os.makedirs("static")
            
            filepath = os.path.join("static", file.filename)
            file.save(filepath)
            
            prediction_data = predict_image(filepath)
            prediction = prediction_data.get("disease") if "error" not in prediction_data else None
            
            return render_template('simple.html', prediction=prediction, prediction_data=prediction_data, 
                             image_filename=file.filename, climate_insights=climate_insights)
    
    return render_template('simple.html', prediction=None, prediction_data=None, image_filename=None, climate_insights=climate_insights)

@app.route('/health')
def health():
    return {"status": "healthy", "service": "Farm Intel", "models_loaded": model is not None}

if __name__ == "__main__":
    print("🌾 Farm Intel - Simple Production Server")
    print("🌐 http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
