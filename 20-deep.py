from keras.preprocessing.image import ImageDataGenerator
from keras.models import Sequential, Model, load_model
from keras.layers import Lambda, Input, Activation, Dropout, Flatten, Dense, Reshape, merge
from keras.layers import Concatenate, Multiply, Conv1D, MaxPool1D, BatchNormalization
from keras import optimizers
from keras.preprocessing.image import ImageDataGenerator
from keras.layers.normalization import BatchNormalization as BN
from keras.layers.core import Dropout
from keras.optimizers import SGD, Adam
from keras import backend as K
from keras.callbacks            import LambdaCallback 


from sklearn.model_selection import StratifiedKFold
import pandas as pd
import copy
import sys
import numpy as np
import pickle
import time
import json
import os

input_tensor = Input( shape=(228,) )

x = input_tensor
x = Dense(100, activation='relu')(x)
x = Dense(100, activation='relu')(x)
x = Dense(100, activation='relu')(x)
x = Dense(1, activation='sigmoid')(x)

model = Model(inputs=input_tensor, outputs=x)

model.compile(loss='binary_crossentropy', optimizer=Adam(), metrics=['mae', 'acc'])
buff = None
now  = time.strftime("%H_%M_%S")
def callback(epoch, logs):
  global buff
  buff = copy.copy(logs)
batch_callback = LambdaCallback(on_epoch_end=lambda batch,logs: callback(batch,logs) )

#gini scoring function from kernel at: 
#https://www.kaggle.com/tezdhar/faster-gini-calculation
def ginic(actual, pred):
  n = len(actual)
  a_s = actual[np.argsort(pred)]
  a_c = a_s.cumsum()
  giniSum = a_c.sum() / a_c[-1] - (n + 1) / 2.0
  return giniSum / n

def gini_normalizedc(a, p):
  return ginic(a, p) / ginic(a, a)

if '--train' in sys.argv:
  Xs, ys  = pickle.load(open('metas/data.pkl', 'rb'))  
  Xst, yst  = pickle.load(open('metas/test.pkl', 'rb'))  
  size = int(len(Xs)*0.2) 
  
  ypreds = {}
  kfold = StratifiedKFold(n_splits = 5 , random_state = 231, shuffle = True)   

  ypreds = np.zeros((np.shape(Xst)[0],5))
  for i,(train_i, test_i) in enumerate(kfold.split(Xs, ys)):
    _Xs, _ys = Xs[train_i], ys[train_i]
    _Xst, _yst = Xs[test_i], ys[test_i]
    
    val_preds = 0
    for j in range(5):
      model.reset_states()
      model.fit(_Xs, _ys, validation_data=(_Xst, _yst), epochs=3, batch_size=260, callbacks=[batch_callback] )
      val_loss = buff['val_loss']
      mae = buff['val_mean_absolute_error']
      acc = buff['val_acc']

      #model.save(f'models/{mae:0.12f}_{acc:0.12f}_{val_loss:0.12f}_{i:09d}.h5')
      xpred = model.predict(_Xst)[:,0]
      val_preds += xpred

      ypreds[:,i] += model.predict(Xst)[:,0] / 5
    cv_gini = gini_normalizedc(_yst, val_preds)
    print(cv_gini)
  y_pred_final = np.mean(ypreds, axis=1)
  print( y_pred_final )
  df_sub = pd.DataFrame({'id' : json.load(fp=open('metas/ids.json')), 
								'target' : y_pred_final},
								columns = ['id','target'])
  df_sub.to_csv('NN_EntityEmbed_5fold-sub.csv', index=False)

if '--submit' in sys.argv:
  os.system('kaggle competitions submit -c porto-seguro-safe-driver-prediction -f NN_EntityEmbed_5fold-sub.csv -m "submission from Kaggle-API"')
  ...
