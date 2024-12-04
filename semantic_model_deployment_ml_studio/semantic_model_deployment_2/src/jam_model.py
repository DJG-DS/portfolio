# Imports
import pandas as pd 
import numpy as np
from transformers import AutoTokenizer, TFAutoModel
import tensorflow as tf
import mlflow

# Parameters
BATCH_SIZE = 16
EPOCHS = 1
CLEAN_TEXT = False
ADD_DENSE = False
DENSE_DIM = 64
ADD_DROPOUT = False
DROPOUT = .2
TRAIN_BASE = True

# Data specific fields
textCol = "text"
clusterCol = "label"


def bert_encode(data, maximum_len):
    input_ids = []
    attention_masks = []

    for iterator in range(len(data.text)):
        encoded = tokenizer.encode_plus(data.text.iloc[iterator],
                                        add_special_tokens = True,
                                        max_length = maximum_len,
                                        pad_to_max_length = True,
                                        return_attention_mask = True)

        input_ids.append(encoded['input_ids'])
        attention_masks.append(encoded['attention_mask'])
    
    return np.array(input_ids), np.array(attention_masks)


def build_model(model_layer, learning_rate, add_dense = ADD_DENSE,
                dense_dim = DENSE_DIM, add_dropout = ADD_DROPOUT, dropout = DROPOUT):
    
    # define inputs
    input_ids = tf.keras.Input(shape = (128,), dtype ='int32')
    attention_masks = tf.keras.Input(shape =(128,), dtype ='int32')

    # insert BERT layer
    sequence_output = model_layer(input_ids, attention_masks)

    # choose only last hidden state
    output = sequence_output[0]
    output = output[:,0,:]

    output = tf.keras.layers.Dense(32, activation = 'relu')(output)
    output = tf.keras.layers.Dense(7, activation = 'softmax')(output) # changed the last layer to 7 from 5 since we have 7 clusters in our data

    # assemble and compile

    model = tf.keras.models.Model(inputs = [input_ids, attention_masks], outputs = output)
    model.compile(tf.keras.optimizers.Adam(learning_rate = learning_rate),
                  loss = 'sparse_categorical_crossentropy', metrics = ['accuracy'])
    
    return model

# start logging
mlflow.start_run()

# enable autologging
mlflow.tensorflow.autolog()


# import data and rename fields - HSBC needs to change this bit to work with their data
train = pd.read_csv('data/train.csv')
train = train[[textCol, clusterCol]]
train.rename(columns={textCol: 'text', clusterCol: 'label'}, inplace=True)

# Import models (from folder in your Azure directory)
pathToHFModels = 'hf_model' # update this path to where you are storing the model
tokenizer = AutoTokenizer.from_pretrained(pathToHFModels)
model = TFAutoModel.from_pretrained(pathToHFModels)

# Tokenize
if TRAIN_BASE:
    train_inputs_ids, train_attention_masks = bert_encode(train, 128)

# Build the model
BERT_base = build_model(model, learning_rate = 1e-5)

# Create a checkpoint
#checkpoint = tf.keras.callbacks.ModelCheckpoint('model/hf_model.h5',
  #  monitor = 'val_loss', save_best_only = True, save_weights_only = True)

# Train the model
if TRAIN_BASE:
    history = BERT_base.fit([train_inputs_ids, train_attention_masks], train.label,
                            validation_split = .2, epochs = EPOCHS)#, callbacks = [checkpoint])

# Save the trained model locally
BERT_base.save('model/custom_bert.h5') # update this path to where you wish to save the mode

mlflow.end_run()

# lots of warnings throughout