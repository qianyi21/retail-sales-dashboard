from __future__ import annotations

import pandas as pd
import streamlit as st

from data_utils import create_sample_data


def load_data() -> pd.DataFrame:
    """
    Return the same dataset currently being used by the app.

    The main page stores the uploaded/sample dataset in
    st.session_state["app_data"] so other pages can access it.
    """

    if "app_data" in st.session_state:
        return st.session_state["app_data"]

    # Fallback if the user opens another page directly.
    data = create_sample_data()

    st.session_state["app_data"] = data

    return data


def apply_filters(data: pd.DataFrame) -> pd.DataFrame:
    """
    Apply the filters currently stored in Streamlit session state.
    """

    filtered_data = data.copy()

    # Month
    if "selected_months" in st.session_state:
        filtered_data = filtered_data[
            filtered_data["MONTH"].isin(
                st.session_state["selected_months"]
            )
        ]

    # Warehouse
    if "selected_warehouses" in st.session_state:
        filtered_data = filtered_data[
            filtered_data["WHOUSE"].isin(
                st.session_state["selected_warehouses"]
            )
        ]

    # Outlet
    if "selected_outlets" in st.session_state:
        filtered_data = filtered_data[
            filtered_data["OUTLET"].isin(
                st.session_state["selected_outlets"]
            )
        ]

    # Supplier
    if "selected_suppliers" in st.session_state:
        filtered_data = filtered_data[
            filtered_data["SUPPLIER"].isin(
                st.session_state["selected_suppliers"]
            )
        ]

    # Department
    if "selected_departments" in st.session_state:
        filtered_data = filtered_data[
            filtered_data["DEPT"].isin(
                st.session_state["selected_departments"]
            )
        ]

    # Class
    if "selected_classes" in st.session_state:
        filtered_data = filtered_data[
            filtered_data["CLASS"].isin(
                st.session_state["selected_classes"]
            )
        ]

    # SKU
    if "selected_skus" in st.session_state:
        filtered_data = filtered_data[
            filtered_data["SKU"].isin(
                st.session_state["selected_skus"]
            )
        ]

    return filtered_data