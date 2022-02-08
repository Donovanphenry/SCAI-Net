from ast import parse
import os
import pandas as pd
import tensorflow as tf
import scai_utils as su
import sys
from sklearn.preprocessing import MultiLabelBinarizer
import argparse

MODEL_BATCH_SIZE = 32
EPOCHS = 3
CHECKPOINT_PATH = 'checkpoints/'
ARCH = 'ResNet50V2'
# MODELS = []

def main():

    training = True

    parser = argparse.ArgumentParser()
    parser.add_argument('-v', action='store_true',
                        help='Verbose mode. Display loss graphs, precision'
                        ' graphs, confusion matrices etc')
    parser.add_argument('-t', action='append', nargs='+', type=str,
                        help='Training mode. Train the next N models that'
                        ' follow this flag.')
    parser.add_argument('-l', action='append', nargs='+', type=str,
                        help='Load mode. Load the next N models that follow'
                        ' this flag from the working directory.')
    parser.add_argument('-e', action='append', nargs='+', type=str,
                        help='Evaluate model. Evaluate the next N models that'
                        ' follow this flag.')
    parser.add_argument('-ts', action='append', nargs='+', type=str,
                        help='Train and save mode. Train the next N models that'
                        ' follow this flag and save each.')


    args = parser.parse_args()
    argc = len(sys.argv)
    arg_dict = vars(args)

    # we might want to switch to constructing separate lists for each argument 
    # accepting lists of models for clarity.
    model_dict = dict()

    # parse command line arguments
    if argc > 1:
        # create dictionary storing model functionality when the script is run
        for arg in arg_dict:
            # ignore arguments that do not switch on functionality for model
            # add them to this list
            if arg in ['v']:
                continue
            # for each list argument, if the model was listed, set the 
            # corresponding value to True
            if arg_dict[arg] != None:
                for arch in arg_dict[arg].pop():
                    if arch not in model_dict:
                        model_dict[arch] = dict()
                    model_dict[arch][arg] = True

    print(f'{model_dict=}')

    # build dataframe containing training data
    train_dataframe = pd.read_csv('data/train_v2.csv').astype(str)
    train_dataframe['image_name'] += '.jpg'
    su.set_NLABELS(train_dataframe)

    # since our task is multilabel classification, we must construct a multi 
    # label binarizer to binarize each of the different labels
    mlb = MultiLabelBinarizer()
    mlb.fit(train_dataframe["tags"].str.split(" "))
    classes = mlb.classes_
    print(f'{classes=}')

    ids = pd.DataFrame(mlb.fit_transform(train_dataframe['tags'].str.split(' ')), columns = classes)

    train_df = pd.concat( [train_dataframe[['image_name']], ids], axis=1 )
    train_dataframe = None

    train_dg, val_dg = su.create_data(train_df, classes)

    print(f'train_df.head =\n{train_df.head(n = 5)}')

    # compute operations on models specified at the command line
    for model_name in model_dict:

        # parse model_dict for the current model
        for operation in model_dict[model_name]:
            if operation == 't':
                is_training = True
            elif operation == 'l':
                is_loaded = True
            elif operation == 'e':
                is_evaluated = True
            elif operation == 'ts':
                is_training = True
                is_saved = True

        if is_training:

            model = su.create_transfer_model(ARCH)
            su.compile_model(model)

            if os.path.isdir(CHECKPOINT_PATH) == False:
                os.mkdir(CHECKPOINT_PATH)

            val_loss_checkpoint = tf.keras.callbacks.ModelCheckpoint(
                filepath=CHECKPOINT_PATH + ARCH + '/',
                monitor='val_loss',
                mode='min',
                save_best_only=True,
            )

            history = model.fit(train_dg,
                epochs = EPOCHS,
                callbacks = [val_loss_checkpoint],
                batch_size = MODEL_BATCH_SIZE,
                validation_data = val_dg,
                verbose = 1
            )
            
            history_df = pd.DataFrame(history.history)
            history_df.head(n = 5)

            su.plot_history(history_df, ('Loss', 'loss'))
            su.plot_history(history_df, ('Precision', 'precision'))
            MODELS.append(('Transfer', model))
        else:
            model = tf.keras.models.load_model(CHECKPOINT_PATH + ARCH + '/')
            MODELS.append(('Transfer', model))
            # precisions = su.evalModels(MODELS, val_dg)
            # for model_name in precisions:
            #     print(f"{model_name}'s precision is {precisions[model_name]:.6f}")

        # su.eyeTestPredictions(model, val_dg, classes)

        # confusion_matrices = su.confusionMatrices(MODELS, val_dg)
        confusion_matrix = su.ensembleConfusion(MODELS, val_dg)
        su.plotEnsembleConfusion(confusion_matrix, classes)
        # su.plotConfusionMatrices(confusion_matrices, classes)

# %%
if __name__ == "__main__":
    main()