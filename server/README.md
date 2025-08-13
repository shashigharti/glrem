# Backend
Workflow for the Omdena pipeline.

# Getting Started

1. **Configure Server**
   - Python 3.12
   - Ubuntu 24.01
   - GDAL 3.9.3
   - venv
   ```bash
   sudo apt update
   sudo apt install python3-venv
   ```

2. **Setup Github ssh**
```bash
ssh-keygen
```
Copy the ssh key to the github.

3. **Clone the repo**
```bash
git clone git@github.com:shashigharti/glrem.git
```

4. **Install pygmstar**
   - Set it to executable
      ```bash
      chmod +x scripts/install.sh
      ```
   - Run the script:
     ```bash
     ./scripts/install.sh
     ```
     * Note make sure that GMTSAR library is installed correctly
   - Set the environment variables, if not set:
     ```bash
     export GMTSAR_PATH=/usr/local/GMTSAR
     export PATH=$GMTSAR_PATH/bin:$PATH
     ```
3. **Create a new virtual environment**
   ```bash
   python3 -m venv envs/glrem
   . envs/glrem
   ```
4. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```
5. **Create the .env file and set the environment variables**
   ```bash
   sudo vi .env
   ```

   ```bash
   Add following variables:

   # User credentials
   USER_USERNAME=admin
   USER_PASSWORD=admin123

   # Directories
   WORKDIR=/home/your_username/python/omdena/glremdata/data/raw_kahr
   DATADIR=/home/your_username/python/omdena/glremdata/data/data_kahr
   OUTPUT=/home/your_username/python/omdena/glremdata/data/output

   # Alaska Satellite Facility
   ASF_USERNAME=333
   ASF_PASSWORD=3333

   # AWS
   AWS_ACCESS_KEY=3333
   AWS_SECRET_KEY=33333

   # Satellite processing
   USE_SAMPLE_BURSTS=true

   # Misc
   LOG_FILENAME=/home/your_username/python/omdena/glrem/server/app.log
   SQLALCHEMY_DATABASE_URL=sqlite:////home/your_username/python/omdena/glrem/glremdata.db

   # Third Party Endpoints
   USGS_ENDPOINT=https://earthquake.usgs.gov/fdsnws/event/1/query
   ```


5. **Install Pre-commit Hooks**
   ```bash
   pre-commit install
   ```

6. **Run the Application**
```
uvicorn main:app --reload
```
The application should be running at http://localhost:8000
