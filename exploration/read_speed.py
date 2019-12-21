import pandas as pd
import numpy as np
import table_operations as to


def reset_data(number):
    #to.clear_tables('race_results')
    new_data = pd.DataFrame(index=range(number))
    new_data['horse_id'] = np.random.choice(range(100), number)
    new_data['race_id'] = 1
    new_data['time'] = 1
    new_data['place'] = np.random.choice([1,2,3,4,5,6,7,8,9], number)
    new_data['winnings'] = np.random.choice([0, 10, 50, 75, 100], number)
    to.insert_dataframe_into_table('race_results', new_data)

reset_data(20)
z = to.whole_table('race_results')