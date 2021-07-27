import numpy as np
import pandas as pd
import pyvista as pv

from umap import UMAP
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import MinMaxScaler
from sklearn.preprocessing import MaxAbsScaler
from typing import Sequence, Tuple, Type


def import_csv_data(path: str = '') -> pd.DataFrame:
    '''
    Creates a pandas dataframe from path to a csv data file.
    '''
    if not path:
        path = input('Enter the path of your csv data file: ')
    return pd.read_csv(path)


def import_vtk_data(path: str = '') -> pd.DataFrame:
    '''
    Creates a pandas dataframe from path to a vtk data file.
    Also returns mesh pyvista object.
    '''
    if not path:
        path = input('Enter the path of your vtk data file: ')

    mesh = pv.read(path)
    
    # Remove vtkGhostType automatically by applying threshold, replace step in paraview.
    if 'vtkGhostType' in mesh.array_names:
        mesh = mesh.threshold(value = [0,0.99], scalars = "vtkGhostType",
               invert=False, continuous = True, preference = "cell",
               all_scalars = False)

    vector_names = []

    # Detect which variables are vectors
    for var_name in mesh.array_names:
        if np.size(mesh.get_array(var_name)) != mesh.n_points:
            vector_names.append(var_name)

    # Make a dataframe from only scalar mesh arrays (i.e. exclude vectors)
    var_names = [name for name in mesh.array_names if name not in vector_names]
    var_arrays = np.transpose([mesh.get_array(var_name) for var_name in var_names])
    df = pd.DataFrame(var_arrays, columns=var_names)

    # Add the vectors back with one row per component
    for vector_name in vector_names:
        # Get dimension of data e.g., 1D or 2D
        data_dim = mesh.get_array(vector_name).ndim

        if data_dim == 1: 
            pass
        else:
            # Get dimension (number of columns) of typical vector
            dim = mesh.get_array(vector_name).shape[1]
            # split data using dim insteady of hard coding
            df[[vector_name + ':' + str(i) for i in range(dim)]] = mesh.get_array(vector_name)

    return df, mesh


def export_vtk_data(mesh: Type, path: str = '', cluster_labels: np.ndarray = None):
    '''
    Exports vtk file with mesh. If cluster labels are passed it
    will include them in a new variable
    '''
    if cluster_labels is not None:
        mesh['clusters'] = cluster_labels
    mesh.save(path)

def clean_data(data: pd.DataFrame, dim: int = 2, vars_to_drop: Sequence[str] = None, vars_to_keep: Sequence[str] = None) -> pd.DataFrame:
    '''    
    Removes ghost cells (if present) and other data columns that
    are not relevant for the dimensionality reduction (i.e. spatial 
    coordinates) from the original data.
    '''
    if dim not in [2, 3]:
        raise ValueError(
            'dim can only be 2 or 3. Use 2 for 2D-plane data and 3 for 3D-volume data')

    cols_to_drop = []

    if 'Points:0' in data.columns:
        cols_to_drop.append(['Points:0', 'Points:1', 'Points:2'])

    if 'vtkGhostType' in data.columns:
        data.drop(data[data.vtkGhostType == 2].index, inplace=True)
        cols_to_drop.append('vtkGhostType')

    if vars_to_keep is not None:
        # Return cleaned data based on preferred var
        cleaned_data = data[["{}".format(var) for var in vars_to_keep]]
    else:
        # drop undesired variables based on 'dim' and 'var_to_drop'
        if 'U:0' in data.columns and dim == 2:
            cols_to_drop.append('U:2')

        if vars_to_drop is not None:
            cols_to_drop.extend(vars_to_drop)

        cleaned_data = data.drop(columns=cols_to_drop, axis=1)
        cleaned_data.reset_index(drop=True, inplace=True)

    return cleaned_data
    
def scale_data(data: pd.DataFrame, scaler: str = 'StandardScaler', feature: str = 'All') -> np.ndarray:
    '''    
    Scales input data based on sklearn standard scaler.
    '''
    scalers = [MinMaxScaler.__name__, StandardScaler.__name__, MaxAbsScaler.__name__]
    if scaler not in scalers:
        raise ValueError(
            'invalid scaler. Expected one of: %s' % scalers)
    if feature not in data.columns:
        raise ValueError(
            'invalid feature. Expected one of: %s' % data.columns)
            
    if feature == 'All':
        print ('Apply scaling for all features.')
        if scaler == 'MinMaxScaler':
            scaled_data = MinMaxScaler().fit_transform(data)
        
        elif scaler == 'StandardScaler':
            scaled_data = StandardScaler().fit_transform(data)
            
        elif scaler == 'MaxAbsScaler':
            scaled_data = MaxAbsScaler().fit_transform(data)
    else: #only support single str feature at the moment
        print ('Apply scaling for single feature {}'.format(feature))
        scaled_data = data.copy()
        
        if scaler == 'MinMaxScaler':
            scaled_data[feature] = MinMaxScaler().fit_transform(data[feature].values.reshape(-1,1))
            
        elif scaler == 'StandardScaler':
            scaled_data[feature] = StandardScaler().fit_transform(data[feature].values.reshape(-1,1))
            
        elif scaler == 'MaxAbsScaler':
            scaled_data[feature] = MaxAbsScaler().fit_transform(data[feature].values.reshape(-1,1))

        
    return scaled_data


def embed_data(data: pd.DataFrame, algorithm, scale: bool = True, scaler: str = 'StandardScaler', feature: str = 'All', **params) -> Tuple[np.ndarray, Type]:
    '''
    Applies either UMAP or t-SNE dimensionality reduction algorithm 
    to the input data (with optional scaling) and returns the
    embedding array. Also accepts specific and optional algorithm 
    parameters.
    '''
    algorithms = [UMAP, TSNE]
    if algorithm not in algorithms:
        raise ValueError(
            'invalid algorithm. Expected one of: %s' % algorithms)

    if scale:
        data = scale_data(data, scaler, feature)

    reducer = algorithm(**params)

    print ('\nData reduction using algorithm: {}....'.format(algorithm.__name__))

    if algorithm == UMAP:
        mapper = reducer.fit(data)
        embedding = mapper.transform(data)
    elif algorithm == TSNE:
        mapper = None
        embedding = reducer.fit_transform(data)

    return embedding, mapper

def _save_emdedding(embedding: np.ndarray, embedding_name: str = None, embedding_path: str = None):

    np.savetxt(embedding_path + embedding_name + '.txt', embedding)
    print('Embedding data saved. \n')
    
def _read_emdedding(embedding_name: str = None, embedding_path: str = None) -> np.ndarray:

    embedding = np.loadtxt(embedding_path + embedding_name + '.txt')
    print('Embedding data read. \n')
        
    return embedding
