import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models, optimizers
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
import data_preprocessing as dp
import viz

# --- CONFIGURATION ---
DATA_DIR = "./data/training_audio/raw/train_set" 
MODEL_SAVE_PATH = "pico_locator.keras"

def create_pico_model(input_shape):
    """
    TinyML Architecture (~26k params).
    Uses GlobalAveragePooling2D to eliminate Flatten() and save RAM.
    """
    inputs = layers.Input(shape=input_shape)
    
    # Block 1
    x = layers.Conv2D(16, (3, 3), padding='same')(inputs)
    x = layers.BatchNormalization()(x)
    x = layers.LeakyReLU(negative_slope=0.1)(x)
    x = layers.MaxPooling2D((2, 2))(x)
    
    # Block 2
    x = layers.Conv2D(32, (3, 3), padding='same')(x)
    x = layers.BatchNormalization()(x)
    x = layers.LeakyReLU(negative_slope=0.1)(x)
    x = layers.MaxPooling2D((2, 2))(x)

    # Block 3
    x = layers.Conv2D(64, (3, 3), padding='same')(x)
    x = layers.BatchNormalization()(x)
    x = layers.LeakyReLU(negative_slope=0.1)(x)
    
    # Global Pooling (The Shrink Ray)
    x = layers.GlobalAveragePooling2D()(x)
    
    # Head
    x = layers.Dropout(0.2)(x) 
    x = layers.Dense(32)(x)
    x = layers.LeakyReLU(negative_slope=0.1)(x)
    outputs = layers.Dense(4, activation='linear')(x) 
    
    return models.Model(inputs=inputs, outputs=outputs, name="PicoLocator_v1")

if __name__ == "__main__":
    # 1. Load & Process Data
    X_train, y_train, X_test, y_test = dp.load_and_split_dataset(DATA_DIR)
    
    if len(X_train) == 0:
        print("No data found!")
        exit()

    indices = np.arange(len(X_train))
    np.random.shuffle(indices)
    X_train = X_train[indices]
    y_train = y_train[indices]

    print("Augmenting data...")
    X_train_aug = dp.augment_data(X_train)
    X_final = np.concatenate([X_train, X_train_aug], axis=0)
    y_final = np.concatenate([y_train, y_train], axis=0)
    
    # 2. Train
    model = create_pico_model(X_final[0].shape)
    model.compile(
        loss=tf.keras.losses.Huber(delta=1.0),
        optimizer=optimizers.Adam(learning_rate=0.001),
        metrics=['mae']
    )
    
    history = model.fit(
        X_final, y_final,
        validation_data=(X_test, y_test),
        epochs=50, 
        batch_size=32,
        callbacks=[
            EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True),
            ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5)
        ]
    )
    
    model.save(MODEL_SAVE_PATH)
    viz.plot_results(model, X_test, y_test, title_prefix="Pico Model")