### Manufacturing Aging Traceability System



This project is a streamlit-based system designed to automate the processing and analysis of aging test results in a manufacturing environment. It reduces manual checking, improve accuracy, and streamlines batch management for operators.





##### Features

* ###### **Batch Scanning**

&nbsp;    - Scan Finished Good (FG) Serial Number (SN) per rack.

&nbsp;    - Organize units into batches by type (Fresh, Rework, OBA).

&nbsp;    - Support multiple racks with configurable unit limits per rack.

&nbsp;    - Automatically update to the latest traceability database to retrieve Control Board (CB) SN, Hash Board (HB) SN, etc.

&nbsp;    - Update CB SN in database to trace the components linked with the FG SN.



* ###### **Automated Result Processing**

&nbsp;    - Automatically detect aging test result (result\_A, result\_B, .zip, and error files) after ending a batch.

&nbsp;    - Reads Result A and B to determine pass/fail status and OBA classification if the IP address is within a fixed range (221-226).

&nbsp;    - Reads .zip and error files to extract error codes/descriptions, HB SN, HB BIN, etc.

&nbsp;    - Updates the database with processed results.



* ###### **Manual Error Handling**

&nbsp;    - Allows operators to manually record units that physically failed (errors not captured by aging test).

&nbsp;    - Supports custom failure reasons for special cases.



* ###### **Batch Management**

&nbsp;    - Start batch (records start time).

&nbsp;    - End batch (records end time and creates result folder).

&nbsp;    - Canceled a batch if necessary.



* ###### **Streamlit interface**

&nbsp;    - Provide a user-friendly web dashboard for monitoring aging results.

&nbsp;    - Display detailed batch summaries by order\_id and rack.





##### Project Structure

aging-traceability/

├── app/                      

│   ├── app.py                				# Main Streamlit application

│   ├── config.py             				# Configuration settings (paths, racks, constants)

│   └── db.py                 				# Database connection and initialization

├── DB/                       

│   ├── AgingAutomation.db              	# SQLite database storing unit and batch records

│   └── Tracking Database.xlsx          	# Traceability Excel file (FG SN, CB SN, HB SN, etc.)

├── sample\_data/              

│   └── 123(order\_id)/

│       └── 260403\_0936 (end batch time and date)/           

│           ├── \*error\*.xlsx     			# Sample error files

│           ├── \*result\_A\*.xlsx          	# Sample result A files

│           ├── \*result\_B\*.xlsx          	# Sample result B files

│           └── Device - \*.zip         	# Sample result ZIP files                  

├── screenshot/               				

│   ├── 1.scan\_page.png

│   ├── 2.manual\_input\_error.png

│   └── 3.scan\_page - after end batch and analysis data.png

├── README.md                 				

└── requirements.txt          				# Python dependencies



##### Requirements

* Python
* Streamlit
* SQLite
* Pandas
* xlwings
* openpyxl



Install dependencies using:

&nbsp;	pip install -r requirements.txt



##### Installation

1. Clone this repository

&nbsp;	git clone <repository\_url>

&nbsp;	cd <repository\_folder>

2\. Create a virtual environment

&nbsp;	python -m venv venv

&nbsp;	source venv/bin/activate   # Linux/Mac

&nbsp;	venv\\Scripts\\activate      # Windows

3\. Install dependencies

&nbsp;	pip install -r requirements.txt

4\. Ensure the database and sample data are in the correct paths (see Project Structure)



##### Usage

Run the Streamlit app:

&nbsp;	streamlit run ./app/app.py

The system provides the following pages:

* Scan FG SN: Scan FG SN and get an overview of scanned units and their status.
* Manual Input Error: Allow operators to input errors for current running failed units 



##### Database

The system uses SQLite (DB/AgingAutomation.db) to store: 

* Scanned units and their details
* Error codes and descriptions



##### Configuration

Edit config.py to set:

* MAX\_PER\_RACK
* RACK\_PC
* BASE\_PATH\_TRACE
* SHARED\_PATH
* DB\_PATH
* TRACE\_DB\_NAME
* DB\_NAME
* ERROR\_CODE\_DESC
* ERROR\_OPTIONS 



##### Screenshots

Screenshots of the system are stored in the screenshot/ folder:





##### Future Improvement

* Perform yield loss analysis
* Create charts to visualize data
* Record root cause for failed units



##### Author

Foo Ke Ting

Email:ktingfoo0527@gmail.com

