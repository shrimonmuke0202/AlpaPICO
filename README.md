# AlpaPICO
### Install Packages

```python
  pip3 install vllm
  pip3 install seqeval
```
 
### Datasets
Dataset is present in the dataset directory
### Run the following code to train the model
```bash
bash train_instruct.sh
```
### Inference
Run the following scrpit to test the best model
```python
  python3 inference_instruct_vllm.py
```
### Prediction
Run the following script and change the input of the prediction.py file with output obtained by running inference code
```python
  python3 prediction.py
```

