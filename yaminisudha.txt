import sqlite3
from decimal import Decimal, ROUND_HALF_UP
conn =sqlite3.connect("payroll.db")
cursor =conn.cursor()
cursor.execute("PRAGMA foreign_keys = ON")
DAYS=["monday","tuesday","wednesday","thursday","friday"]
employees={}
PAY_RATES={}
def create_tables():
    cursor.execute("""
    create table if not exists pay_rates(
    category text primary key,
    regular_rate integer not null check(regular_rate > 0),
    overtime_allowed integer not null check(overtime_allowed in (0, 1)))
    """)
    cursor.execute("""
    create table if not exists working_days(
    day_name text primary key,
    day_order integer not null unique check(day_order between 1 and 5))
    """)
    cursor.execute("""
    create table if not exists employees(emp_id text primary key, name text not null check(length(trim(name))>0),category text not null,foreign key(category) references pay_rates(category)) """)
    cursor.execute("""
    create table if not exists timesheets(
        emp_id text not null,
        day_name text not null,
        in_hour integer not null check(in_hour between 0 and 23),
        in_minute integer not null check(in_minute between 0 and 59),
        out_hour integer not null check(out_hour between 0 and 23),
        out_minute integer not null check(out_minute between 0 and 59),
        break_minutes integer not null check(break_minutes >=0),
        worked_minutes integer not null check(worked_minutes >=0),
        regular_minutes integer not null check(regular_minutes >=0),
        overtime_minutes integer not null check(overtime_minutes>=0),
        status text not null check(status in ('Present', 'Short Day', 'Absent')),
        is_late integer not null check(is_late in (0, 1)),
        day_pay real not null check(day_pay >=0),
        primary key(emp_id, day_name),
        foreign key(emp_id) references employees(emp_id),
        foreign key(day_name) references working_days(day_name))""")
    conn.commit()
def insert_data():
    rates =[("junior",200,1),("senior",300,1),("intern",120,0)]
    for rate in rates:
        cursor.execute("""insert or ignore into pay_rates values (?,?,?) """,rate)
    for i, day in enumerate(DAYS, start=1):
        cursor.execute("""insert or ignore into working_days values(?,?)""",(day,i))
    conn.commit()
def load_data():
    employees.clear()
    PAY_RATES.clear()
    cursor.execute("""select category,regular_rate,overtime_allowed from pay_rates""")
    for category,rate,overtime in cursor.fetchall():
        PAY_RATES[category]={
            "regular_rate":rate,
            "overtime_allowed":overtime
        }
    cursor.execute("""select emp_id, name, category from employees """)
    for emp_id,name,category in cursor.fetchall():
        employees[emp_id]= {
            "name":name,
            "category":category,
            "timesheets":{}
        }
    cursor.execute("""select emp_id, day_name, in_hour, in_minute,out_hour, out_minute, break_minutes,worked_minutes, regular_minutes,overtime_minutes, status, is_late, day_pay from timesheets""")
    for row in cursor.fetchall():
        emp_id =row[0]
        day =row[1]
        if emp_id in employees:
            employees[emp_id]["timesheets"][day] = {
                "in_hour":row[2],
                "in_minute":row[3],
                "out_hour":row[4],
                "out_minute":row[5],
                "break_minutes":row[6],
                "worked_minutes":row[7],
                "regular_minutes":row[8],
                "overtime_minutes":row[9],
                "status":row[10],
                "is_late":row[11],
                "day_pay":row[12]
            }
def read_integer(message,minimum=None,maximum=None):
    while True:
        try:
            number=int(input(message))
            if minimum is not None and number<minimum:
                print("Value is too small")
            elif maximum is not None and number>maximum:
                print("Value is too large")
            else:
                break
        except ValueError:
            print("please enter a valid whole number")
    return number
def register_employees():
    no_of_employees=read_integer("how many employees do you want to register? ", 1)
    count=0
    while count<no_of_employees:
        emp_id=input("enter employee ID: ").strip()
        if not emp_id:
            print("employee ID cannot be empty")
            continue
        if emp_id in employees:
            print("employee ID already exists")
            continue
        name=input("enter employee name: ").strip()
        if not name:
            print("Employee name cannot be empty.")
            continue
        category=input("enter category junior,senior,intern: ").strip().casefold()
        if category not in ("junior", "senior", "intern"):
            print("Invalid category.")
            continue
        try:
            cursor.execute("""insert into employees values (?,?,?) """,(emp_id,name,category))
            conn.commit()
            count +=1
            print("Employee registered successfully")
        except sqlite3.IntegrityError:
            conn.rollback()
            print("Employee registration failed Check employee ID or category")
        except sqlite3.Error:
            conn.rollback()
            print("Database error")
    load_data()
def read_time(message):
    print(message)
    hour=read_integer("enter hour (0-23): ",0,23)
    minute=read_integer("enter minute (0-59): ",0,59)
    total_minutes=hour*60+minute
    return hour,minute,total_minutes
def collect_timesheet():
    load_data()
    if len(employees)<2:
        print("at least 2 employees must be registered first")
        return
    emp_id=input("enter employee ID: ").strip()
    if emp_id not in employees:
        print("employee ID does not exist")
        return
    day=input("enter day monday-friday: ").strip().casefold()
    if day not in DAYS:
        print("invalid working day")
        return
    if day in employees[emp_id]["timesheets"]:
        print("timesheet already entered for this day")
        return
    in_hour,in_minute,in_total=read_time("enter in-time")
    out_hour,out_minute,out_total=read_time("enter out-time")
    if out_total<=in_total:
        print("out-time must be later than in-time")
        return
    total_duration=out_total-in_total
    break_minutes=read_integer("enter break duration in minutes: ",0)
    if break_minutes>total_duration:
        print("break cannot be greater than the total time")
        return 
    worked_minutes=total_duration-break_minutes
    regular_minutes,overtime_minutes,status,is_late,day_pay=calculate_daily_pay(emp_id,worked_minutes,in_total)
    try:
        cursor.execute("""insert into timesheets values (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,(emp_id,day,in_hour,in_minute,out_hour,out_minute,break_minutes,worked_minutes,regular_minutes,overtime_minutes,status,is_late,float(day_pay)))
        conn.commit()
        print("Timesheet entered successfully.")
        print(f"Worked time:{worked_minutes//60}:{worked_minutes%60}")
        print("Status:",status)
        print("Daily pay: Rs.", f"{day_pay:.2f}")
        load_data()
    except sqlite3.IntegrityError:
        conn.rollback()
        print("Timesheet already exists or database constraint failed")
    except sqlite3.Error:
        conn.rollback()
        print("Database error. Timesheet was not saved")
def calculate_daily_pay(emp_id,worked_minutes,in_total):
    category=employees[emp_id]["category"]
    regular_rate =PAY_RATES[category]["regular_rate"]
    overtime_allowed =PAY_RATES[category]["overtime_allowed"]
    STANDARD_MINUTES=480
    SHORT_DAY_MINUTES=240
    MAXIMUM_OVERTIME_MINUTES=180
    if worked_minutes>=STANDARD_MINUTES:
        status="Present"
    elif worked_minutes>=SHORT_DAY_MINUTES:
        status="Short Day"
    else:
        status="Absent"
    if in_total>(9*60+15):
        is_late=1
    else:
        is_late=0
    if status=="Absent":
        regular_minutes=0
    elif status=="Short Day":
        regular_minutes=worked_minutes
    else:
        regular_minutes=min(worked_minutes,STANDARD_MINUTES)
    overtime_minutes=0
    if status=="Present" and overtime_allowed==1:
        extra_minutes=worked_minutes-STANDARD_MINUTES
        overtime_minutes =min(extra_minutes,MAXIMUM_OVERTIME_MINUTES)
    regular_pay=(Decimal(regular_minutes)*Decimal(regular_rate)/Decimal(60))
    overtime_pay=(Decimal(overtime_minutes)*Decimal(regular_rate)*Decimal("1.5")/Decimal(60))
    day_pay = (regular_pay + overtime_pay).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return (regular_minutes,overtime_minutes,status,is_late,day_pay)
def format_minutes(minutes):
    hours=minutes // 60
    remaining_minutes=minutes % 60
    return f"{hours:02d}:{remaining_minutes:02d}"

def missing_timesheets():
    cursor.execute("""
    select e.emp_id,wd.day_name
    from employees e
    cross join working_days wd
    left join timesheets t
        on e.emp_id=t.emp_id
        and wd.day_name=t.day_name
    where t.emp_id is null
    order by wd.day_order,e.emp_id
    """)
    missing=cursor.fetchall()
    if not missing:
        print("All employee timesheets are completed.")
        return
    print("\nMissing Timesheets")
    for emp_id, day in missing:
        print("Employee ID:",emp_id, "| Day:",day)
def timesheets_complete():
    cursor.execute("""
    select count(*)
    from employees e
    where (
        select count(*)
        from timesheets t
        where t.emp_id=e.emp_id
    )<5
    """)
    incomplete_count=cursor.fetchone()[0]
    return incomplete_count==0
def calculate_payroll():
    load_data()
    if not employees:
        print("No employees registered")
        return []
    if not timesheets_complete():
        print("Payroll cannot be generated")
        print("Please enter all five days for every employee")
        return []
    payroll=[]
    for emp_id, employee in employees.items():
        category =employee["category"]
        regular_rate =PAY_RATES[category]["regular_rate"]
        present =0
        short_days =0
        absent =0
        late_marks =0
        total_regular_minutes =0
        total_overtime_minutes = 0
        gross_pay = Decimal("0")
        for day, sheet in employee["timesheets"].items():
            if sheet["status"] =="Present":
                present +=1
            elif sheet["status"] =="Short Day":
                short_days +=1
            else:
                absent += 1
            late_marks += sheet["is_late"]
            total_regular_minutes += sheet["regular_minutes"]
            total_overtime_minutes += sheet["overtime_minutes"]
            gross_pay +=Decimal(str(sheet["day_pay"]))
        if late_marks >=3:
            deduction =Decimal(2*regular_rate)
        else:
            deduction =Decimal("0.00")
        net_pay = gross_pay-deduction
        payroll.append({"emp_id": emp_id,"name": employee["name"],"category": category,"present": present,"short_days": short_days,"absent": absent,"late_marks": late_marks,"regular_minutes": total_regular_minutes,"overtime_minutes": total_overtime_minutes,"gross_pay": gross_pay,"deduction": deduction,"net_pay": net_pay})
    #payroll.sort(key=lambda employee:(-employee["net_pay"],employee["late_marks"]))
    for i in range(1,len(payroll)):
        key =payroll[i]
        j =i-1
        while j >=0:
            if payroll[j]["net_pay"] <key["net_pay"]:
                payroll[j+1] =payroll[j]
                j =j-1
            elif payroll[j]["net_pay"] ==key["net_pay"] and payroll[j]["late_marks"] > key["late_marks"]:
                payroll[j+1] =payroll[j]
                j -= 1
            else:
                break
        payroll[j+1] =key
    return payroll
def display_payroll():
    payroll = calculate_payroll()
    if not payroll:
        return
    print("------weekly payroll ------")
    for rank, employee in enumerate(payroll, start=1):
        print("\nRank:", rank)
        print("Employee ID:", employee["emp_id"])
        print("Name:", employee["name"])
        print("Category:", employee["category"])
        print("Present:", employee["present"])
        print("Short Days:", employee["short_days"])
        print("Absent:", employee["absent"])
        print("Late Marks:", employee["late_marks"])
        print("Regular Hours:",format_minutes(employee["regular_minutes"]))
        print("Overtime Hours:",format_minutes(employee["overtime_minutes"]))
        print("Gross Pay: Rs.",f"{employee['gross_pay']:.2f}")
        print("Deduction: Rs.",f"{employee['deduction']:.2f}")
        print("Net Pay: Rs.",f"{employee['net_pay']:.2f}")
def category_wise_report():
    if not timesheets_complete():
        print("Complete all employee timesheets before generating this report")
        return
    cursor.execute("""
        select e.category,
            count(distinct e.emp_id),
            sum(t.regular_minutes),
            sum(t.overtime_minutes),
            sum(t.day_pay),
            avg(t.day_pay)
        from employees e
        join timesheets t
            ON e.emp_id = t.emp_id
        GROUP BY e.category
        ORDER BY e.category
    """)
    report = cursor.fetchall()
    print("category wise report")
    for row in report:
        category=row[0]
        employee_count=row[1]
        regular_minutes=row[2]
        overtime_minutes=row[3]
        total_gross_pay=row[4]
        average_gross_pay= row[5]
        print("Category:", category)
        print("Number of Employees:",employee_count)
        print("Total Regular Hours:",regular_minutes//60,"hours",regular_minutes % 60,"minutes")
        print("Total Overtime Hours:",overtime_minutes//60,"hours",overtime_minutes % 60,"minutes")
        print("Total Gross Pay: Rs.",f"{total_gross_pay:.2f}")
        print("Average Gross Pay: Rs.",f"{average_gross_pay:.2f}")
def main():
    create_tables()
    insert_data()
    load_data()
    while True:
        print("--------employe weekly payroll system-------")
        print("1.Register employees")
        print("2.Enter timesheet")
        print("3.Check missing timesheets")
        print("4.Generate payroll summary")
        print("5.Category-wise report")
        print("6.Exit")
        choice = input("Enter your choice: ").strip()
        if choice=="1":
            register_employees()
        elif choice=="2":
            collect_timesheet()
        elif choice=="3":
            missing_timesheets()
        elif choice=="4":
            display_payroll()
        elif choice=="5":
            category_wise_report()
        elif choice=="6":
            print("Thank you!")
            break
        else:
            print("Invalid menu choice please try again")
main()