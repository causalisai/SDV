from unittest.mock import patch

import pandas as pd
import pytest
from copulas.multivariate.gaussian import GaussianMultivariate

from sdv.constraints import UniqueCombinations
from sdv.tabular.copulagan import CopulaGAN
from sdv.tabular.copulas import GaussianCopula
from sdv.tabular.ctgan import CTGAN, TVAE

MODELS = [
    CTGAN(epochs=1),
    TVAE(epochs=1),
    GaussianCopula(),
    CopulaGAN(epochs=1),
]


@pytest.mark.parametrize('model', MODELS)
def test_conditional_sampling_graceful_reject_sampling_True_dict(model):
    data = pd.DataFrame({
        'column1': list(range(100)),
        'column2': list(range(100)),
        'column3': list(range(100))
    })

    model.fit(data)
    conditions = {
        'column1': 28,
        'column2': 37,
        'column3': 93
    }

    with pytest.raises(ValueError):
        model.sample(1, conditions=conditions, graceful_reject_sampling=True)


@pytest.mark.parametrize('model', MODELS)
def test_conditional_sampling_graceful_reject_sampling_True_dataframe(model):
    data = pd.DataFrame({
        'column1': list(range(100)),
        'column2': list(range(100)),
        'column3': list(range(100))
    })

    model.fit(data)
    conditions = pd.DataFrame({
        'column1': [28],
        'column2': [37],
        'column3': [93]
    })

    with pytest.raises(ValueError):
        model.sample(conditions=conditions, graceful_reject_sampling=True)


@pytest.mark.parametrize('model', MODELS)
def test_conditional_sampling_graceful_reject_sampling_False_dict(model):
    data = pd.DataFrame({
        'column1': list(range(100)),
        'column2': list(range(100)),
        'column3': list(range(100))
    })

    model.fit(data)
    conditions = {
        'column1': 28,
        'column2': 37,
        'column3': 93
    }

    with pytest.raises(ValueError):
        model.sample(1, conditions=conditions)


@pytest.mark.parametrize('model', MODELS)
def test_conditional_sampling_graceful_reject_sampling_False_dataframe(model):
    data = pd.DataFrame({
        'column1': list(range(100)),
        'column2': list(range(100)),
        'column3': list(range(100))
    })

    model.fit(data)
    conditions = pd.DataFrame({
        'column1': [28],
        'column2': [37],
        'column3': [93]
    })

    with pytest.raises(ValueError):
        model.sample(conditions=conditions)


@patch('sdv.tabular.copulas.copulas.multivariate.GaussianMultivariate',
       spec_set=GaussianMultivariate)
def test_conditional_sampling_constraint_uses_reject_sampling(gm_mock):
    """Test that the ``sample`` method handles constraints with conditions.

    The ``sample`` method is expected to properly apply constraint
    transformations by dropping columns that cannot be conditonally sampled
    on due to them being part of a constraint if ``fit_columns_model``
    is False.

    Setup:
    - The model is being passed a ``UniqueCombination`` constraint and then
    asked to sample with two conditions, one of which the constraint depends on.
    The constraint is expected to skip its transformations since only some of
    the columns are provided by the conditions and the model will use reject
    sampling to meet the constraint instead.

    Input:
    - Conditions
    Side Effects:
    - Correct columns to condition on are passed to underlying sample method
    """
    # Setup
    constraint = UniqueCombinations(
        columns=['city', 'state'],
        handling_strategy='transform',
        fit_columns_model=False
    )
    data = pd.DataFrame({
        'city': ['LA', 'SF', 'CHI', 'LA', 'LA'],
        'state': ['CA', 'CA', 'IL', 'CA', 'CA'],
        'age': [27, 28, 26, 21, 30]
    })
    model = GaussianCopula(constraints=[constraint], categorical_transformer='label_encoding')
    sampled_numeric_data = [pd.DataFrame({
        'city#state': [0, 1, 2, 0, 0],
        'age': [30, 30, 30, 30, 30]
    }), pd.DataFrame({
        'city#state': [1],
        'age': [30]
    })]
    gm_mock.return_value.sample.side_effect = sampled_numeric_data
    model.fit(data)

    # Run
    conditions = {'age': 30, 'state': 'CA'}
    sampled_data = model.sample(5, conditions=conditions)

    # Assert
    expected_transformed_conditions = {'age': 30}
    expected_data = pd.DataFrame({
        'city': ['LA', 'SF', 'LA', 'LA', 'SF'],
        'state': ['CA', 'CA', 'CA', 'CA', 'CA'],
        'age': [30, 30, 30, 30, 30]
    })
    sample_calls = model._model.sample.mock_calls
    assert len(sample_calls) == 2
    model._model.sample.assert_any_call(5, conditions=expected_transformed_conditions)
    model._model.sample.assert_any_call(1, conditions=expected_transformed_conditions)
    pd.testing.assert_frame_equal(sampled_data, expected_data)


@patch('sdv.tabular.copulas.copulas.multivariate.GaussianMultivariate',
       spec_set=GaussianMultivariate)
def test_conditional_sampling_constraint_uses_columns_model(gm_mock):
    """Test that the ``sample`` method handles constraints with conditions.

    The ``sample`` method is expected to properly apply constraint
    transformations by sampling the missing columns for the constraint
    if ``fit_columns_model`` is True.

    Setup:
    - The model is being passed a ``UniqueCombination`` constraint and then
    asked to sample with two conditions, one of which the constraint depends on.
    The constraint will sample the columns it needs that are not present in
    the conditions and will then use constraint transformations to meet the
    requirements.

    Input:
    - Conditions
    Side Effects:
    - Correct columns to condition on are passed to underlying sample method
    """
    # Setup
    constraint = UniqueCombinations(
        columns=['city', 'state'],
        handling_strategy='transform'
    )
    data = pd.DataFrame({
        'city': ['LA', 'SF', 'CHI', 'LA', 'LA'],
        'state': ['CA', 'CA', 'IL', 'CA', 'CA'],
        'age': [27, 28, 26, 21, 30]
    })
    model = GaussianCopula(constraints=[constraint], categorical_transformer='label_encoding')
    sampled_numeric_data = [pd.DataFrame({
        'city#state': [2],
        'age': [30]
    }), pd.DataFrame({
        'city#state': [1, 1, 0, 0, 0],
        'age': [30, 30, 30, 30, 30]
    }), pd.DataFrame({
        'city#state': [0, 0, 1, 1, 1],
        'age': [30, 30, 30, 30, 30]})
    ]
    gm_mock.return_value.sample.side_effect = sampled_numeric_data
    model.fit(data)

    # Run
    conditions = {'age': 30, 'state': 'CA'}
    sampled_data = model.sample(5, conditions=conditions)

    # Assert
    expected_states = pd.Series(['CA', 'CA', 'CA', 'CA', 'CA'], name='state')
    expected_ages = pd.Series([30, 30, 30, 30, 30], name='age')
    sample_calls = model._model.sample.mock_calls
    assert len(sample_calls) >= 2 and len(sample_calls) <= 3
    assert all(c[2]['conditions']['age'] == 30 for c in sample_calls)
    assert all('city#state' in c[2]['conditions'] for c in sample_calls)
    pd.testing.assert_series_equal(sampled_data['age'], expected_ages)
    pd.testing.assert_series_equal(sampled_data['state'], expected_states)
    assert all(c in ('SF', 'LA') for c in sampled_data['city'])
