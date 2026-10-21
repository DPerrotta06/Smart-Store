def normalizeEmail(email: str):
    usernamePart,domainPart=email.split('@',1)
    if "." in usernamePart:
        usernamePartClean=usernamePart.replace(".","")
        cleanEmail=f"{usernamePartClean}@{domainPart}"
        return cleanEmail.lower()
    return email.lower()
    

        
    
