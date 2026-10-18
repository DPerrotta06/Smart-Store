from flask import Blueprint, request, redirect, render_template
from Model.customerModel import Customer
import uuid
import re


customer_bp=Blueprint('customer_bp',__name__, template_folder='../View')

@customer_bp.route('/', methods=['GET'])
@customer_bp.route('/add_customer',methods=['GET'])
def showingform():
    return render_template('signup.html')


@customer_bp.route('/temperature',methods=['GET'])
def temperaturePage():
    return render_template('temperature.html')


@customer_bp.route('/add_customer',methods=['POST'])
def addingcustomer():
    first_name=request.form.get('first_name')
    last_name=request.form.get('last_name')
    tel_number=request.form.get('tel_number')
    email=request.form.get('email')
    customer_address=request.form.get('customer_address')
    #regex
    patternForName=r"^[A-Z][a-z]+$"
    patternForTel=r"^\d{3}-\d{3}-\d{4}"
    patternForEmail=r"^(?=.{6,30}@)[a-z0-9]+(?:\.[a-z0-9]+)*@gmail\.com$",re.IGNORECASE
    try:
        #if statements for firstlast / tel / email optionally:address 
        #if something wrong it should render_template('error.html',message)
        new_customer=Customer( 
            first_name=first_name,
            last_name=last_name,
            tel_number=tel_number,
            email=email,
            customer_address=customer_address,
            customer_uuid=str(uuid.uuid4())
        )
        
        new_customer.save()#will change to method that checks and saves and will take customer
        message=f"added customer"
    except Exception as e:
        message=f"Cant add customer: {e}"

    return render_template('signup.html', message=message)
