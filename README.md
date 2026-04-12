# Manufacturing Aging Traceability System



This project is a streamlit-based system designed to automate the processing and analysis of aging test results in a manufacturing environment. It reduces manual checking, improve accuracy, and streamlines batch management for operators.





##### Features (Updated)



###### **Batch Scanning**

     - Scan Finished Good (FG) Serial Number (SN) per rack.

     - Organize units into batches by type (Fresh, Rework, OBA).

     - Support multiple racks with configurable unit limits per rack.

     - Automatically update to the latest traceability database to retrieve Control Board (CB) SN, Hash Board (HB) SN, etc.

     - Update CB SN in database to trace the components linked with the FG SN.



###### **Automated Result Processing**

     - Automatically detect aging test result (result\_A, result\_B, .zip, and error files) after ending a batch.

     - Reads Result A and B to determine pass/fail status and OBA classification if the IP address is within a fixed range (221-226).

     - Reads .zip and error files to extract error codes/descriptions, HB SN, HB BIN, etc.

     - Updates the database with processed results.



###### **Manual Error Handling**

     - Allows operators to manually record units that physically failed (errors not captured by aging test).

     - Supports custom failure reasons for special cases.



###### **Batch Management**

     - Start batch (records start time).

     - End batch (records end time and creates result folder).

     - Canceled a batch if necessary.



###### **Streamlit interface**

     - Provide a user-friendly web dashboard for monitoring aging results.

     - Display detailed batch summaries by order\_id and rack.



###### **Troubleshooting Records (New)**

     - Allows engineers to update root cause, action taken and status by selecting Batch ID with SN.

     - Saves changes to database for traceability.

     - Provide a full table view of all troubleshooting records.



###### **Visualizations (Updated!)**

     - **Error Frequency Bar Chart** - shows the frequency of each error for a selected order\_id.

     	- Provides engineers a clear view of which errors happen most often.

 	- Helps prioritize issues that need immediate attention.

     - **Top-5 Error Pie Chart** - displays the five most frequent error codes as a pie chart.

 	- Offers a quick visual summary of the most impactful errors.

 	- Makes it easy to spot which errors dominate the order at a glance.

     - **Root Cause Bar Chart** - shows the frequency of each identified root cause for a selected order\_id.

     	- Helps engineers understand which underlying issues contribute most to failures.

 	- Supports prioritization of corrective actions based on impact.

     - **Top-5 Root Cause Pie Chart** - shows the proportion of the top root causes in a pie chart.

 	- Provides a quick overview of how different root causes are distributed.

 	- Makes it easy to identify the dominant cause affecting the order.

##### 

##### 

##### Project Structure



aging-traceability/

├── app/

│   ├── app.py                				# Main Streamlit application

│   ├── charts.py             				# Visualization functions: error bar, top5 pie chart

│   ├── config.py             				# Configuration settings (paths, racks, constants)

│   ├── db.py             				# Database connection and initialization

│   └── func.py                 			# Helper functions

├── DB/

│   ├── AgingAutomation.db              	# SQLite database storing unit and batch records

│   └── Tracking Database.xlsx          	# Traceability Excel file (FG SN, CB SN, HB SN, etc.)

├── sample\_data/

│   └── 123(order\_id)/

│       └── 260403\_0936 (end batch time and date)/

│           ├── \*error\*.xlsx     			# Sample error files

│           ├── \*result\_A\*.xlsx          		# Sample result A files

│           ├── \*result\_B\*.xlsx          		# Sample result B files

│           └── Device - \*.zip         			# Sample result ZIP files

├── screenshot/

│   ├── 1.scan-fg-sn-page.png

│   ├── 2.manual-input-physical-error-after-start-batch.png

│   ├── 3.scan-fg-sn-page-after-end-batch-dashboard.png

│   ├── 4. troubleshooting-record-edit-form.png

│   ├── 5. error-bar-chart.png

│   ├── 5.1 error-table.png

│   ├── 5.2 error-pie-chart.png

│   ├── 5.3 root-cause-bar-chart.png

│   ├── 5.4 root-cause-table.png

│   └── 5.5 root-cause-pie-chart

├── README.md

└── requrements.txt          			# Python dependencies



##### 

##### Requirements

* Python
* Streamlit
* SQLite
* Pandas
* xlwings
* openpyxl
* numpy
* matplotlib



Install dependencies using:

 	pip install -r requirements.txt





### Installation

1\. Clone this repository



 	git clone <repository\_url>

 	cd <repository\_folder>



2\. Create a virtual environment



 	python -m venv venv

 	source venv/bin/activate  	# Linux/Mac

 	venv\\Scripts\\activate      	# Windows



3\. Install dependencies

 	pip install -r requirements.txt



4\. Ensure the database and sample data are in the correct paths (see Project Structure)





##### Usage

Run the Streamlit app:



 	streamlit run ./app/app.py



The system provides the following pages:



* Scan FG SN: Scan FG SN and get an overview of scanned units and their status.
* Manual Input Error: Allow operators to input errors for current running failed units
* Troubleshooting Records: Allow engineer to update root cause, action taken and status by selecting Batch ID with SN.
* Charts: Data visualization by selecting order\_id, including error bar chart, root cause bar chart and top-5 pie chart







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

Screenshots of the system are stored in the screenshot/ folder

##### 

##### 

##### Future Improvement

* Perform yield loss analysis
* Create charts to visualize data - **UPDATED!**

  * Error bar chart for errors by order\_id
  * Top-5 error pie chart
  * Root cause bar chart for errors by order\_id
  * Top-5 root cause pie chart
* Record root cause for failed units - **UPDATED!**





Author

Foo Ke Ting

Email:ktingfoo0527@gmail.com

