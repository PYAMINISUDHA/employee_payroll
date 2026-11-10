import sqlite3
conn = sqlite3.connect("payroll.db")
cursor = conn.cursor()
cursor.execute("PRAGMA foreign_keys = ON")
cursor.execute("""
create table if not exists pay_rates(category text PRIMARY KEY not null,regular_rate Decimal not null,overtime_rate Decimal not null)
""")
cursor.execute("""create table working_days(day_name text Primary Key,day_order)""")




def main():
    while True:
        choice = int(input("enter the choice : "))
        if choice == 1:
            Register_employee()
        elif choice == 2:
            Enter_timesheets()
        elif choice == 3:
            Checking_missing_timesheet()
        elif choice == 4:
            Generate_pay_rolle_summary()
        elif choice == 5:
            categorey_wise_report()
        elif choice == 6:
            break
        else:
            print("Enter Your Choice : ") 

main()
