# Dashboard assets

Place static files here for the Streamlit UI.

## Logo (placeholder)

- **Expected file:** `logo.png` (square, ~128–256 px, transparent or dark background)
- **Current behavior:** The sidebar uses a temporary icon from icons8 until `logo.png` is added.
- **To use your logo:** Save the image as `dashboard/assets/logo.png` and update `dashboard/components/sidebar.py` to load it:

  ```python
  st.sidebar.image("dashboard/assets/logo.png", width=64)
  ```

No other assets are required for 1.0.0.
