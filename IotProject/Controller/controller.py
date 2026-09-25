from flask import Blueprint, request, redirect, render_template
from Model.model import Customer
from Controller.hardware import success,failure

customer_bp=Blueprint('customer_bp',__name__, template_folder='../View')

@customer_bp.route('/', methods=['GET'])
@customer_bp.route('/add_customer',methods=['GET'])
def showingform():
    return render_template('view.html')

@customer_bp.route('/add_customer',methods=['POST'])
def addingcustomer():
    first_name=request.form.get('first_name')
    last_name=request.form.get('last_name')
    tel_number=request.form.get('tel_number')
    email=request.form.get('email')
    customer_address=request.form.get('customer_address')
    try:
        #raise Exception("Test error - forcing failure")
        new_customer=Customer(
            first_name=first_name,
            last_name=last_name,
            tel_number=tel_number,
            email=email,
            customer_address=customer_address
        )
        new_customer.save()
        success()
        message=f"added customer"
    except Exception as e:
        failure()
        message=f"Cant add customer: {e}"

    return render_template('view.html', message=message)
