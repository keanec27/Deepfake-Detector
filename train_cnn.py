from keras.preprocessing.image import ImageDataGenerator
from keras.layers import GlobalAveragePooling2D
from keras.layers import Dropout, Dense
from keras.models import Model
from keras.optimizers.legacy import Nadam
from keras.callbacks import ModelCheckpoint, EarlyStopping
from keras.callbacks import CSVLogger
from sklearn.model_selection import train_test_split
from keras.applications.xception import Xception
from keras.applications.resnet50 import ResNet50
from keras.applications.inception_v3 import InceptionV3
from keras.applications.inception_resnet_v2 import InceptionResNetV2
from keras.applications.nasnet import NASNetLarge
from keras.applications import EfficientNetB5, EfficientNetB0
from matplotlib import pyplot as plt
from keras import backend as K
import tensorflow as tf
tf.compat.v1.disable_eager_execution()
import numpy as np
import time
import argparse
from os.path import exists
from os import makedirs


def cnn_model(model_name, img_size):
    """
    Model definition using Xception net architecture
    """
    input_size = (img_size, img_size, 3)
    if model_name == "xception":
        baseModel = Xception(
            weights="imagenet",
            include_top=False,
            input_shape=(img_size, img_size, 3)
        )
    elif model_name == "iv3":
        baseModel = InceptionV3(
            weights="imagenet",
            include_top=False,
            input_shape=(img_size, img_size, 3)
        )
    elif model_name == "irv2":
        baseModel = InceptionResNetV2(
            weights="imagenet",
            include_top=False,
            input_shape=(img_size, img_size, 3)
        )
    elif model_name == "resnet":
        baseModel = ResNet50(
            weights="imagenet",
            include_top=False,
            input_shape=(img_size, img_size, 3)
        )
    elif model_name == "nasnet":
        baseModel = NASNetLarge(
            weights="imagenet",
            include_top=False,
            input_shape=(img_size, img_size, 3)
        )
    elif model_name == "ef0":
        baseModel = EfficientNetB0(
            input_size,
            weights="imagenet",
            include_top=False
        )
    elif model_name == "ef5":
        baseModel = EfficientNetB5(
            input_size,
            weights="imagenet",
            include_top=False
        )

    headModel = baseModel.output
    headModel = GlobalAveragePooling2D()(headModel)
    headModel = Dense(512, activation="relu", kernel_initializer="he_uniform")(
        headModel
    )
    headModel = Dropout(0.4)(headModel)
    # headModel = Dense(512, activation="relu", kernel_initializer="he_uniform")(
    #     headModel
    # )
    # headModel = Dropout(0.5)(headModel)
    headModel = Dropout(0.5)(headModel)
    predictions = Dense(
        2,
        activation="softmax",
        kernel_initializer="he_uniform")(
        headModel
    )
    model = Model(inputs=baseModel.input, outputs=predictions)

    for layer in baseModel.layers:
        layer.trainable = True

    optimizer = Nadam(
        lr=0.002, beta_1=0.9, beta_2=0.999, epsilon=1e-08
    )
    model.compile(
        loss="categorical_crossentropy",
        optimizer=optimizer,
        metrics=["accuracy"]
    )
    return model


def main():
    start = time.time()

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "-e", "--epochs", required=True, type=int,
        help="Number of epochs", default=25
    )
    ap.add_argument(
        "-m", "--model_name", required=True, type=str,
        help="Imagenet model to train", default="xception"
    )
    ap.add_argument(
        "-w",
        "--weights_save_name",
        required=True,
        type=str,
        help="Model wieghts name"
    )
    ap.add_argument(
        "-b", "--batch_size", required=True, type=int,
        help="Batch size", default=16
    )
    ap.add_argument(
        "-im_size",
        "--image_size",
        required=True,
        type=int,
        help="Batch size",
        default=224,
    )
    args = ap.parse_args()

    # Training dataset loading
    train_data = np.load("/content/train_data_25_c40.npy")
    train_label = np.load("/content/train_label_25_c40.npy")
    train_data=train_data[:10000]
    train_label=train_label[:10000]
    print("Dataset Loaded...")

    # Train and validation split
    trainX, valX, trainY, valY = train_test_split(
        train_data, train_label, test_size=0.2, shuffle=False
    )
    print(trainX.shape, valX.shape, trainY.shape, valY.shape)

    # Train nad validation image data generator
    trainAug = ImageDataGenerator(
        rescale=1.0 / 255.0,
        rotation_range=30,
        zoom_range=0.15,
        width_shift_range=0.2,
        height_shift_range=0.2,
        shear_range=0.15,
        horizontal_flip=True,
        fill_mode="nearest",
    )

    valAug = ImageDataGenerator(rescale=1.0 / 255.0)

    model = cnn_model(args.model_name, img_size=args.image_size)

    # Number of trainable and non-trainable parameters
    trainable_count = int(
        np.sum([K.count_params(p) for p in set(model.trainable_weights)])
    )
    non_trainable_count = int(
        np.sum([K.count_params(p) for p in set(model.non_trainable_weights)])
    )

    print("Total params: {:,}".format(trainable_count + non_trainable_count))
    print("Trainable params: {:,}".format(trainable_count))
    print("Non-trainable params: {:,}".format(non_trainable_count))

    if not exists("/content/CNN/trained_wts"):
        makedirs("/content/CNN/trained_wts")
    if not exists("/content/CNN/training_logs"):
        makedirs("/content/CNN/training_logs")
    if not exists("/content/CNN/plots"):
        makedirs("/content/CNN/plots")

    # Keras backend
    model_checkpoint = ModelCheckpoint(
        "/content/CNN/trained_wts/" + args.weights_save_name + ".hdf5",
        monitor="val_loss",
        verbose=1,
        save_best_only=True,
        save_weights_only=True,
    )

    stopping = EarlyStopping(monitor="val_loss", patience=10, verbose=0)
    csv_logger = CSVLogger(
        "/content/CNN/training_logs/xception.log",
        separator=",",
        append=True,
    )

    print("Training is going to start in 3... 2... 1... ")
    
    # Model Training
    H = model.fit_generator(
        trainAug.flow(trainX, trainY, batch_size=args.batch_size),
        steps_per_epoch=len(trainX) // args.batch_size,
        validation_data=valAug.flow(valX, valY),
        validation_steps=len(valX) // args.batch_size,
        epochs=args.epochs,
        callbacks=[model_checkpoint, stopping, csv_logger],
    )

    # plot the training loss and accuracy
    plt.style.use("ggplot")
    plt.figure()
    N = stopping.stopped_epoch + 1
    plt.plot(np.arange(0, N), H.history["loss"], label="train_loss")
    plt.plot(np.arange(0, N), H.history["val_loss"], label="val_loss")
    plt.plot(np.arange(0, N), H.history["accuracy"], label="train_acc")
    plt.plot(np.arange(0, N), H.history["val_accuracy"], label="val_acc")
    plt.title("Training Loss and Accuracy")
    plt.xlabel("Epoch #")
    plt.ylabel("Loss/Accuracy")
    plt.legend(loc="lower left")
    plt.savefig("/content/CNN/plots/training_plot.png")

    end = time.time()
    dur = end - start

    if dur < 60:
        print("Execution Time:", dur, "seconds")
    elif dur > 60 and dur < 3600:
        dur = dur / 60
        print("Execution Time:", dur, "minutes")
    else:
        dur = dur / (60 * 60)
        print("Execution Time:", dur, "hours")


if __name__ == "__main__":
    main()