import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models, optimizers
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
import data_preprocessing as dp
import viz

# --- CONFIGURATION ---
DATA_DIR = "./data/training_audio/raw/train_set" 
MODEL_SAVE_PATH = "binaural_model_v1_full.keras"

def create_production_model(input_shape):
    """
    The 'Big Brain' Architecture (~4M params).
    Uses standard Flatten() and large Dense layers.
    """
    model = models.Sequential()
    
    # Block 1
    model.add(layers.Conv2D(32, (3, 3), padding='same', input_shape=input_shape))
    model.add(layers.BatchNormalization()) 
    model.add(layers.LeakyReLU(negative_slope=0.1))
    model.add(layers.MaxPooling2D((2, 2)))
    
    # Block 2
    model.add(layers.Conv2D(64, (3, 3), padding='same'))
    model.add(layers.BatchNormalization())
    model.add(layers.LeakyReLU(negative_slope=0.1))
    model.add(layers.MaxPooling2D((2, 2)))

    # Block 3
    model.add(layers.Conv2D(128, (3, 3), padding='same'))
    model.add(layers.BatchNormalization())
    model.add(layers.LeakyReLU(negative_slope=0.1))
    model.add(layers.MaxPooling2D((2, 2)))
    
    # Flatten creates massive connection matrix
    model.add(layers.Flatten())
    
    # Dense Block
    model.add(layers.Dense(256))
    model.add(layers.LeakyReLU(negative_slope=0.1))
    model.add(layers.Dropout(0.3)) 
    
    model.add(layers.Dense(128))
    model.add(layers.LeakyReLU(negative_slope=0.1))
    model.add(layers.Dropout(0.3))

    model.add(layers.Dense(4, activation='linear')) 
    
    return model

if __name__ == "__main__":
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
    
    model = create_production_model(X_final[0].shape)
    
    model.compile(loss=tf.keras.losses.Huber(delta=1.0), 
                  optimizer=optimizers.Adam(learning_rate=0.0005), 
                  metrics=['mae'])
    
    history = model.fit(
        X_final, y_final,
        validation_data=(X_test, y_test),
        epochs=50, 
        batch_size=32,
        callbacks=[
            EarlyStopping(monitor='val_loss', patience=8, restore_best_weights=True),
            ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=3)
        ]
    )
    
    model.save(MODEL_SAVE_PATH)
    viz.plot_results(model, X_test, y_test, title_prefix="Big Model")