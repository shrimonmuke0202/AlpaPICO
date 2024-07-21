import pandas as pd
from metric import calculate_metrics_from_dataframe

prediction = pd.read_json('models_inference.json')
# prediction.head(3)

ENTITY_TYPES=['OUT','INT','PAR']
# ENTITY_TYPES=['OUT']


metrics = calculate_metrics_from_dataframe(prediction, ENTITY_TYPES)

final_prec = (metrics['INT']['precision'] + metrics['OUT']['precision'] + metrics['PAR']['precision'])/3
final_rec = (metrics['INT']['recall'] + metrics['OUT']['recall'] + metrics['PAR']['recall'])/3
final_f1 = (metrics['INT']['f1'] + metrics['OUT']['f1'] + metrics['PAR']['f1'])/3

print("Precision", final_prec)
print("Recall",    final_rec)
print("F1",    final_f1)
