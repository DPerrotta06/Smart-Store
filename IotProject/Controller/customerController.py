from flask import Blueprint, request, redirect, render_template
from Model.customerModel import Customer,saveCustomer,selectCustomerByEmail
from GeneralFunction.generalFunction import normalizeEmail
import uuid
import re


customer_bp=Blueprint('customer_bp',__name__, template_folder='../View/html',static_folder='../View/css')

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
    message=""
    
    
    #regex
    patternForName=r"^[A-Z][a-z]+$"
    patternForTel=r"^\d{3}-\d{3}-\d{4}$"
    patternForEmail=r"^(?=.{6,30}@)[a-zA-Z0-9]+(?:\.[a-z0-9]+)*@gmail\.com$" 
    error=False

    if not re.fullmatch(patternForName,first_name):
        error=True
        message+="The first name is incorrect: Only Letters\n"
    if not re.fullmatch(patternForName,last_name):
        error=True
        message+="The last name is incorrect: Only Letters\n"
    if not re.fullmatch(patternForTel,tel_number):
        error=True
        message+="The telephone is incorrect: 111-111-1111\n"
    if not re.fullmatch(patternForEmail,email):
        error=True
        message+="The email is incorrect: example.ch05@gmail.com or example@gmail.com\n"
    if(error==False):
        emailNormalized=normalizeEmail(email)
        modelResponse=selectCustomerByEmail(emailNormalized)
        if modelResponse:
            message="Customer already exists"
            return render_template("signup.html",message=message),400
        else:
            message="added customer"
            new_customer=Customer( 
                        first_name=first_name,
                        last_name=last_name,
                        tel_number=tel_number,
                        email=emailNormalized,
                        customer_address=customer_address,
                        customer_uuid=str(uuid.uuid4())
                        )
            saveCustomer(new_customer)
            return render_template("signup.html",message=message),201
           
    return render_template('signup.html', message=message),400
