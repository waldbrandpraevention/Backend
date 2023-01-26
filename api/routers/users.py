
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from database import users_table
from database import organizations_table
from validation import *
from api.dependencies.classes import Token

from ..dependencies.authentication import create_access_token, get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES
from ..dependencies.users import *

router = APIRouter()



@router.get("/users/me/", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """API call to get the curret user we are communicating with

    Args:
        current_user (User, optional): User. Defaults to Depends(get_current_user).

    Returns:
        User: Current user with only the basic infos (no password)
    """
    return current_user

@router.get("/users/me/allerts/", status_code=status.HTTP_200_OK)
async def read_users_me_allerts(current_user: User = Depends(get_current_user)):
    """API call to get the curret users allerts

    Args:
        current_user (User, optional): User. Defaults to Depends(get_current_user).

    Returns:
        str[]: List of allerts
    """
    return await get_user_allerts(current_user)

@router.post("/users/login/", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """API call to create an access token

    Args:
        form_data (OAuth2PasswordRequestForm, optional): Login data. Defaults to Depends().

    Raises:
        HTTPException: Raises error if the email or password or incorrect

    Returns:
        dict: Token information in json format
    """
    
    #note: username is the reserved name for the login name, must be used even if we are using email
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/users/signup/", status_code=status.HTTP_201_CREATED)
async def register(email: str = Form(), password: str = Form(), first_name: str = Form(), last_name: str = Form(), organization: str = Form()):
    """API call to create a new account

    Args:
        email (str, optional): Email. Defaults to Form().
        password (str, optional): Plaintext password. Defaults to Form().
        first_name (str, optional): Frist name. Defaults to Form().
        last_name (str, optional): Last name Defaults to Form().

    Raises:
        HTTPException: _description_
        HTTPException: _description_

    Returns:
        _type_: _description_
    """
    errors = []
    errors.extend(validate_email(email))
    errors.extend(validate_password(password))
    errors.extend(validate_first_name(first_name))
    errors.extend(validate_last_name(last_name))
    errors.extend(validate_organization(organization))
    if len(errors) > 0:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail=errors,
        )
    if get_user(email):
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="This email is already assosiated with an existing account",
        )
    
    hashed_pw = get_password_hash(password)
    organization_obj = organizations_table.get_orga(organization) 
    user = UserWithSensitiveInfo(   email=email,
                                    first_name=first_name,
                                    last_name=last_name,
                                    hashed_password=hashed_pw,
                                    organization= organization_obj,
                                    permission=1,
                                    disabled=0,
                                    email_verified=0)
    
    users_table.create_user(user)
    return {"message": "success"}


@router.post("/users/me/update", status_code=status.HTTP_200_OK)
async def change_user_info(current_user: User = Depends(get_current_user), 
                           email: str | None = None, password: str | None = None,
                           first_name: str | None = None, last_name: str | None = None,
                           organization: str | None = None):
    """API call to update the current user

    Args:
        current_user (User, optional): _description_. Defaults to Depends(get_current_user).
        email (str | None, optional): new email. Defaults to None.
        password (str | None, optional): password. Defaults to None.
        first_name (str | None, optional): new first name. Defaults to None.
        last_name (str | None, optional): new ast name. Defaults to None.
        organization (str | None, optional): new organization. Defaults to None.

    Returns:
        _type_: _description_
    """
    
    update_helper(current_user,email,password,first_name,last_name, organization)

    return {"updated:", "not implemented yet"}

def update_helper(current_user:User, 
                  email: str | None,
                  password: str| None,
                  first_name: str| None,
                  last_name: str| None, 
                  organization: str| None,
                  permission: int | None,
                  disabled: bool |None,
                  email_verified:bool|None
                  ):
    errors = []
    update_sql_dictr = {}
    if email and email != current_user.email:
        if get_user(email):
            errors.extend("This email is already assosiated with an existing account")
        else:
            errors.extend(validate_email(email))
            update_sql_dictr[users_table.UsrAttributes.EMAIL] = email
    if password:
        errors.extend(validate_password(password))
        hashed_pw = get_password_hash(password)
        update_sql_dictr[users_table.UsrAttributes.PASSWORD] = hashed_pw
    if first_name:
        errors.extend(validate_first_name(first_name))
        update_sql_dictr[users_table.UsrAttributes.FIRST_NAME] = first_name
    if last_name:
        errors.extend(validate_last_name(last_name))
        update_sql_dictr[users_table.UsrAttributes.LAST_NAME] = last_name
    if organization:
        errors.extend(validate_organization(organization))
        organization_obj = organizations_table.get_orga(organization)
        if not organization_obj:
            errors.append('orga doesnt exist.')
        else:
            update_sql_dictr[users_table.UsrAttributes.ORGA_ID] = organization_obj.id
    if permission:
        errors.extend(validate_permission(permission))
        update_sql_dictr[users_table.UsrAttributes.PERMISSION] = permission
    if disabled != None:
        update_sql_dictr[users_table.UsrAttributes.DISABLED] = disabled
    if email_verified != None:
        update_sql_dictr[users_table.UsrAttributes.EMAIL_VERIFIED] = email_verified

    if len(errors) > 0:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail=errors,
        )

    if len(update_sql_dictr)==0:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail='Nothing to update.',
        )

    col_str =""
    valarr= []
    for col, value in update_sql_dictr.items():
        col_str+= f'{col}=?,'
        valarr.append(value)
    col_str = col_str[:-1]

    users_table.update_user_withsql(current_user.id,col_str,valarr)