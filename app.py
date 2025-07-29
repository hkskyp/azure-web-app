import streamlit as st

pg = st.navigation(
    {
        "Developer":[
            st.Page("azure-float-bits.py", title="IEEE 754 Floating Point Bit Representation Analyzer", icon="🔢"),
            st.Page("azure-coordinate-converter.py", title="Geographic Coordinate Converter", icon="🗺️")
        ]
    }
)
pg.run()