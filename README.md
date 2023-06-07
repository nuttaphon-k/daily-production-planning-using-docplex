# daily-production-planning-using-docplex

This alghorithm is created to solve a problem which is daily production planning. The constraint programming modeling (CP) is applied to solve the problem using DOcplex. DOcplex is a native Python modeling library for optimization developed by IBM<sup>[[1]](#references)</sup>. The explanation and example of the CP can be read in the link<sup>[[2]](#references)</sup>. Basically, the CP can be broken into three steps: describing the problem, modeling the problem and finding solutions to the model of the problem. The DOcplex document about the CP can be found here<sup>[[3]](#references)</sup>.

The production planning which is the problem is how to arrange the production into time schedule which can achieve the optimal objective of the problem. There are serveral machines and serveral materials. The machine can process specific groups of materials. Orders include the required amount of materials and deadlines. It also takes more time to change materials in one machine. Therefore, it is necessary to plan production appropriately in order to manage production on time and reduce time to adjust machines to change materials.

The constraints and objective of this problem are explained as the followings.

### Constraints

1. All jobs must be done.
2. No overlap between jobs and add adjustment time if changing a material.

### Objective
1. Minimize the sum of time that exceed the deadline of all jobs and time used for machine adjustment due to changing a material.
```
sum(Weight1 * sum(time exceed deadline) + Weight2 * sum(time for machine adjustment))
```
---
## How to buid
The program is built using pyinstaller which a python library for building an EXE file from a python project. The step how to build are explained in a step as the followings.

1. Install python (if already have go to next step).
    * on Linux: follow this https://docs.python-guide.org/starting/install3/linux/.
    * on Mac: the python already exists.
    * on Windows: download and install from this link https://www.python.org/downloads/.
2. Clone the project and go to project directory via terminal (Mac or Linux) / command line (Windows).
    * `cd <Directory of project>`
3. Install virtual environment using pip.
    * `pip install virtualenv`
4. Create virtual environment named venv.
    * `python -m venv venv` or `python3 -m venv venv`
5. Activate virtual environment.
    * For Mac or Linux.
        * `source venv/bin/activate`
    * For Windows.
        * `venv/Script/activate`
6. Install required python libraries.
    * `pip install -r requirements.txt`
7. Create dbconfig.json.
    * Duplicate file dbconfig_template.json.
    * Rename to dbconfig.json.
    * Change the database credentials in the file.
8. Build the program using `bash` for windows `bash` is needed to install from git (https://git-scm.com/download/win) and add paths to environment variable by following this link (https://linuxhint.com/add-git-to-path-windows/)
    * For Mac or Linux
        * `bash build.sh`
    * For Windows
        * `bash build_win.sh`
9. The two folders which are dist and build will appear after finish step 8. The exe file named planner can be found in dist folder.

## User guide
After open or execute the program, the terminal or command line will appears. If open for the first time it may take some times for initialization. The log in terminal or command line will appear as the following steps.
```
16:26:33 main INFO Connect to the database ...
16:26:33 main INFO The connection to the database was successful.
16:26:33 main INFO ------------------------------------------------
16:26:33 main INFO Start production planning
16:26:33 main INFO Default start date: 2023-06-08
>>Do you want to change start date (Y/n):
```
1. The program will ask a user whether a user want to change the start date of the planning or not. The default start date is shown in the above line. If need type `Y` and press enter. If not type `n` and press enter.
```
>>>enter start date (YYYY-MM-DD):
```
2. If need to change the start date, the following line is for adding a specific start date. A user must enter date in specific format which is YYYY-MM-DD (ex. 2022-01-01).
```
>>>Do you have a holiday in next two weeks (Y/n):
```
3. If in the next two weeks there are holidays, type `Y` and press enter.
```
>>>enter holiday in format (YYYY-MM-DD,YYYY-MM-DD): 
```
4. Add holiday in the specify format. For example, "2022-01-02,2022-01-03" (without a double quote).
```
>>>Do you want to plan with OT (Y/n):
```
5. If an OT is included in the planning, type `Y` and press enter.
6. After that the program will generate the production plan and store in the database.
```
16:36:19 production_planning INFO Select machine type: 1.
16:36:19 production_planning INFO Number of machines: 4.
16:36:19 production_planning INFO Number of jobs: 4.
16:36:19 planner INFO Start planning ...
16:36:30 planner INFO Success.
16:36:30 planner INFO Objective value is 0
16:36:30 planner INFO Tardy job objective value: 0
16:36:30 planner INFO Adjustment time objective value: 0
16:36:30 scheduler INFO Start scheduling ...
16:36:30 scheduler INFO Success.

16:37:11 production_planning INFO Scheduling succeeded.
16:37:11 production_planning INFO Insert schedule to the database ...
16:37:11 production_planning INFO Success.
16:37:11 production_planning INFO The overall objective value is 46

```
7. An objective value will be shown after finish a scheduling for each machine type and the overall objective value will be shown after finish all machine types.
```
16:37:11 production_planning INFO The so_id that are not processed in this planning are 399, 399, 399, 399, 499, 541, 541, 541, 541, 561, 561, 561, 561, 561, 561, 578, 578, 578, 578, 581, 584, 584, 589, 589, 589, 589, 589, 589, 593, 593, 593, 593, 593, 593, 601, 601, 605, 605, 610, 610, 610, 610, 610, 616, 616, 616, 616, 616, 616, 620, 620, 622, 622, 622, 622, 622, 624, 624, 624, 624, 624, 633, 635, 635, 637, 640, 640, 644, 644, 645, 645, 645, 645, 649, 650, 653
```
8. The so_id that are not included in the planning will be shown.
9. Press enter to close a program.

## References
* [1] https://www.ibm.com/docs/en/icos/12.9.0?topic=docplex-python-modeling-api
* [2] https://towardsdatascience.com/constraint-programming-explained-2882dc3ad9df
* [3] https://www.ibm.com/docs/en/icos/12.8.0.0?topic=optimizer-constraint-programming-cp