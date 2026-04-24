### **Manufacturing Aging Traceability System**

This project is a streamlit-based system designed to automate the processing and analysis of aging test results in a manufacturing environment. It reduces manual checking, improves accuracy, and streamlines batch management for operators.





##### **Features (Updated)**

###### **Batch Scanning**

&nbsp; - Scan Finished Good (FG) Serial Number (SN) per rack.

&nbsp; - Organize units into batches by type (Fresh, Rework, OBA).

&nbsp; - Support multiple racks with configurable unit limits per rack.

&nbsp; - Automatically update to the latest traceability database to retrieve Control Board (CB) SN, Hash Board (HB) SN, etc.

&nbsp; - Update CB SN in database to trace the components linked with the FG SN.



###### **Automated Result Processing**

&nbsp; - Automatically processes results from a designated result directory after batch completion.

&nbsp; - Reads Result A and B to determine pass/fail status and OBA classification if the IP address is within a fixed range (221-226).

&nbsp; - Reads .zip and error files to extract error codes/descriptions, HB SN, HB BIN, etc.

&nbsp; - Updates the database with processed results.



###### **Manual Error Handling**

&nbsp; - Allows operators to manually record units that physically failed (errors not captured by aging test).

&nbsp; - Supports custom failure reasons for special cases.



###### **Batch Management**

&nbsp; - Start batch (records start time).

&nbsp; - End batch (records end time and creates result folder).

&nbsp; - Cancel a batch if necessary.



###### **Streamlit Interface**

&nbsp; - Provide a user-friendly web dashboard for monitoring aging results.

&nbsp; - Display detailed batch summaries by "order\_id" and rack.



###### **Troubleshooting Records**

&nbsp; - Allows engineers to update root cause, action taken and status by selecting Batch ID with SN.

&nbsp; - Maintains full audit history of troubleshooting actions per SN and batch.

&nbsp; - Provide a full table view of all troubleshooting records.



###### **Analytics Dashboard Features (Updated!)**

&nbsp; - **Yield Loss Line Chart (Added!)**

&nbsp;	- Shows the yield loss of each batch for a selected "order\_id".

&nbsp;	- Provides engineers with a clear view of yield loss per batch.

&nbsp;	- Helps identify problematic batches quickly for further investigation.



&nbsp; - **Error Frequency Bar Chart** 

&nbsp;	- Shows the frequency of each error for a selected "order\_id".

&nbsp; 	- Provides engineers with a clear view of which errors occur most often.

&nbsp; 	- Helps prioritize issues that need immediate attention.



&nbsp; - **Top-5 Error Pie Chart** 

&nbsp;	- Displays the five most frequent error codes as a pie chart.

&nbsp; 	- Offers a quick visual summary of the most impactful errors.

&nbsp; 	- Makes it easy to spot which errors dominate the order at a glance.



&nbsp; - **Root Cause Bar Chart** 

&nbsp;	- Shows the frequency of each identified root cause for a selected "order\_id".

&nbsp; 	- Helps engineers understand which underlying issues contribute most to failures.

&nbsp; 	- Supports prioritization of corrective actions based on impact.



&nbsp; - **Top-5 Root Cause Pie Chart** 

&nbsp;	- Shows the proportion of the top root causes in a pie chart.

&nbsp; 	- Provides a quick overview of how different root causes are distributed.

&nbsp; 	- Makes it easy to identify the dominant cause affecting the order.





##### **Project Structure**

aging-traceability/

├── app/

│ ├── \_\_init\_\_.py 		

│ ├── main.py				# Main Streamlit application

│ ├── app\_controller.py	# Controls the main application workflow (Streamlit UI actions).

│ ├── chart.py 			# Visualization functions: yield loss chart, error bar, top5 pie chart

│ ├── setting.py 			# Configuration settings (paths, racks, constants)

│ ├── database.py 			# Database connection and initialization

│ ├── state.py 			# Initializes application state (e.g., Streamlit session\_state default values)

│ ├── service/

│ │   │

│ │   ├── \_\_init\_\_.py

│ │   ├── aging\_service.py				# Aging test logic and failure counting

│ │   ├── batch\_service.py				# Batch time range and batch-related queries

│ │   ├── common\_service.py			# Contains shared utility database queries used across multiple services.

│ │   ├── failure\_excel\_service.py		# Processes Excel-based failure logs

│ │   ├── failure\_zip\_service.py		# Processes ZIP-based failure logs

│ │   ├── summary\_service.py			# Generates scan summary reports from raw unit\_records data.

│ │   ├── traceability\_service.py 		# Traceability Excel loading, refresh, and mapping dictionaries

│ │   └── troubleshooting\_service.py 	# Manages troubleshooting records and database updates

├── DB/

│ ├── AgingAutomation.db 			# SQLite database storing unit and batch records

│ └── Tracking Database.xlsx 		# Traceability Excel file (FG SN, CB SN, HB SN, etc.)

├── sample\_data/

│ └── 123(order\_id)/

│ └── 260403\_0936 (end batch time and date)/

│ ├── \*error\*.xlsx 		# Sample error files

│ ├── \*result\_A\*.xlsx 		# Sample result A files

│ ├── \*result\_B\*.xlsx 		# Sample result B files

│ └── Device - \*.zip 		# Sample result ZIP files

├── screenshot/

│ ├── 1.0.scan-fg-sn-page.png

│ ├── 1.1.scan-fg-sn-page-scanning-fg-sn.png

│ ├── 1.2.scan-fg-sn-page-after-start-batch.png

│ ├── 2.manual-input-error-physically-failed-unit-page.png

│ ├── 3.0.scan-fg-sn-page-after-end-batch-checking-files.png

│ ├── 3.1.scan-fg-sn-page-after-end-batch-done-processing-result.png

│ ├── 3.2.scan-fg-sn-page-end-batch-dashboard.png

│ ├── 4. troubleshooting-record-edit-form.png

│ ├── 5.0.yield-loss-chart.png

│ ├── 5.1.yield-loss-table.png

│ ├── 5.2.error-bar-chart.png

│ ├── 5.3.error-table.png

│ ├── 5.4.error-pie-chart.png

│ ├── 5.5.root-cause-bar-chart.png

│ ├── 5.6.root-cause-table.png

│ └── 5.7.root-cause-pie-chart.png

├── README.md

└── requrements.txt 		# Python dependencies





##### **Requirements**

* Python 3.9+
* Streamlit
* SQLite
* Pandas
* xlwings
* openpyxl
* numpy
* matplotlib



**Install dependencies using:**

  pip install -r requirements.txt





##### **Installation**

**1. Clone this repository**



  git clone <repository\_url>

  cd <repository\_folder>



**2. Create a virtual environment**



  python -m venv venv

  source venv/bin/activate 	# Linux/Mac

  venv\\Scripts\\activate 	# Windows



**3. Install dependencies**



  pip install -r requirements.txt



**4. Ensure the database and sample data are in the correctly placed:**

Ensure the following are correctly placed:

* SQLite database file (DB/AgingAutomation.db)
* Traceability Excel file (DB/Tracking Database.xlsx)
* Required folder structure as defined in Project Structure





##### **Usage**

Run the Streamlit app:



   streamlit run ./app/main.py





##### **System Features**

The system provides the following modules:



* **Scan FG SN**

&nbsp;  - Scan FG SN input

   - View scanned unit status and rack allocation

   - Real-time scan summary dashboard



* **Manual Input Error**

   - Allow operators to manually input failure reasons

   - Used for current running failed units



* **Troubleshooting Records**

   - Engineers can update:

&nbsp;	- Root cause

&nbsp;	- Action taken

&nbsp;	- Troubleshooting status

   - Filter by Batch ID and SN



* **Charts \& Analytics**

   - Data visualization based on selected order\_id:

&nbsp;	- Yield loss line chart

&nbsp;	- Error bar chart 

&nbsp;	- Root cause bar chart

&nbsp;	- Top-5 error pie chart

&nbsp;	- Top-5 root cause pie chart





##### **Database**

The system uses SQLite (DB/AgingAutomation.db) to store:

* Scanned unit records
* Aging results
* Error codes \& descriptions
* Troubleshooting records





##### **Configuration**

Edit config.py to adjust system settings:



* MAX\_PER\_RACK 	# Maximum SN per rack
* RACK\_PC 		# Rack-to-PC mapping
* BASE\_PATH\_TRACE 	# Traceability file path
* SHARED\_PATH 		# Shared network path
* DB\_PATH 		# SQLite database path
* TRACE\_DB\_NAME 	# Traceability file name
* DB\_NAME 		# Database file name
* ERROR\_CODE\_DESC 	# Error code mapping
* ERROR\_OPTIONS 	# Allowed error selection list





##### **Screenshots**

Screenshots of the system are stored in: 

screenshot/ 





##### **Future Improvement**

✔ Yield loss analysis (Completed)

✔ Data visualization dashboard (Completed)



**Charts added:**

* Error distribution by order\_id
* Root cause analysis charts
* Top-5 error pie chart
* Top-5 root cause pie chart



**Additional improvements:**

* Enhanced troubleshooting workflow (Completed)
* Improved root cause tracking system (Completed)





##### **Author**

Foo Ke Ting

Email:ktingfoo0527@gmail.com

