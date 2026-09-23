# scripts

Entry-point scripts for the YOLO workflows: scene/SAFE detection (`detect.py`),
serving (`serve.py`), drift backtracking (`hindcast.py`), and coastline
downloads (`download_coastlines.py`). Scripts are thin wrappers around the
`oilspill` package — they parse arguments and call into library code.
