import pandas as pd
import numpy as np
from transformers import AutoTokenizer
from transformers import TFAutoModel

# define the function to encode any new text coming in
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

# import the tokenizer model
tokenizer = AutoTokenizer.from_pretrained('distilbert-base-uncased')

# get the data (this would be the input to the endpoint,
# potentially a list of sentences or a table)
test = pd.read_csv('data/test.csv')

# import model - from model registry?
import os
model_path = os.path.join(os.environ["AZUREML_MODEL_DIR"], "JAM-model")
model = TFAutoModel.from_pretrained("models/custom_bert.h5")

# encode the new/test data
test_input_ids, test_attention_masks = bert_encode(test, 128)

# predict
preds = BERT_base.predict([test_input_ids, test_attention_masks])

# flatten predictions - converts predictions to cluster values
flattened_preds = []
for pred in preds:
    flattened_preds.append(np.argmax(pred))

# collate predictions in the test dataset 
# (probably will not need to do this for the first version of the endpoint,
# just return the clusters as a list/array)
test.loc[:, 'label_pred'] = flattened_preds