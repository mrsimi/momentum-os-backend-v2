from contextlib import contextmanager
from datetime import datetime, timezone
import json
import logging
from pprint import pprint
import paystack
from app.core.database import SessionLocal
from app.models.user_model import UserModel
from app.schemas.auth_schema import SubscriptionResponse
from app.schemas.response_schema import BaseResponse
from fastapi import status
import os 
from dotenv import load_dotenv

load_dotenv()

from app.models.subscription_model import PlansModel, UserSubscriptionModel, WebhookLogsModel

logging.basicConfig(
    format="%(asctime)s [%(process)d] [%(levelname)s] %(message)s",
    level=logging.INFO
)


class SubscriptionService:
    def __init__(self):
        self.db = SessionLocal()
        self.paystack = paystack
        self.paystack.api_key = os.getenv("PAY_SECRET_KEY")

    def __del__(self):
        self.db.close()

    @contextmanager
    def get_session(self):
        try:
            yield self.db
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        finally:
            self.db.close()
    
    def subscribe_to_plan(self, user_id:int, plan_id=1)-> BaseResponse[str]:
        try:
            with self.get_session() as db:
                user = db.query(UserModel).filter(UserModel.id == user_id).first()
                if not user:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="User not found",
                        data=None
                    )

                if not user.is_active:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="User is not active",
                        data=None
                    )
                
                plan = db.query(PlansModel).filter(PlansModel.id == plan_id).first()
                if not plan:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Invalid plan type",
                        data=None
                    )
                
                #validate if they have a subscription 
                user_subscription = db.query(UserSubscriptionModel).filter(
                    UserSubscriptionModel.user_id == user_id,
                    UserSubscriptionModel.plan_id == plan_id
                ).first()
                
                if user_subscription and user_subscription.is_active:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="User has a valid subscription",
                        data=None
                    )
                
                #create user / get user on provider
                create_user_response = self.paystack.Customer.create(email=user.email)
                if create_user_response.status == False:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Cannot complete subscription now. Kindy try again",
                        data=None
                    )
                
                external_customer_id = create_user_response.data['id']
                #validate if user has subscription. if they do update the subscription table. 
                subscription_for_user_plan = paystack.Subscription.list(
                    plan=plan.external_plan_id,
                    customer = external_customer_id
                )
                #pprint(subscription_for_user_plan)
                if subscription_for_user_plan.status == False:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Cannot complete subscription now. Kindy try again",
                        data=None
                    )
                
                if subscription_for_user_plan.data:
                    last_subscription = subscription_for_user_plan.data[-1]
                    if last_subscription['status'] in ['active', 'non-renewing']:
                        if user_subscription:
                            user_subscription.stage = last_subscription['status']
                            user_subscription.next_payment_date = last_subscription['next_payment_date']
                            user_subscription.is_active = True
                            user_subscription.external_customer_id = external_customer_id
                        else:
                            # Should not happen due to unique check — but handle gracefully
                            user_subscription = UserSubscriptionModel(
                                user_id=user_id,
                                plan_id=plan.id,
                                stage=last_subscription['status'],
                                external_customer_id=external_customer_id,
                                provider='paystack',
                                next_payment_date=last_subscription['next_payment_date'],
                                is_active=True,
                            )
                            db.add(user_subscription)
                        
                        db.commit()
                        return BaseResponse(
                            statusCode=status.HTTP_400_BAD_REQUEST,
                            message="User already has a valid subscription",
                            data=None
                        )
                response = paystack.Transaction.initialize(
                    email=user.email,
                    amount=1,  # Replace with real amount
                    plan=plan.external_plan_code,
                    channels=['card'],
                    callback_url=os.getenv("FRONTEND_URL")+'/dashboard'
                )

                if not response.status:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Cannot complete subscription now. Kindly try again",
                        data=None
                    )

                print(response.data)

                if user_subscription:
                    user_subscription.stage = 'initialize'
                    user_subscription.external_customer_id = external_customer_id
                    user_subscription.external_transaction_ref = response.data['reference']
                    user_subscription.is_active = False
                    user_subscription.date_updated = datetime.now(timezone.utc) 
                else:
                    user_subscription = UserSubscriptionModel(
                        user_id=user_id,
                        plan_id=plan.id,
                        stage='initialize',
                        external_customer_id=external_customer_id,
                        provider='paystack',
                        is_active=False,
                        external_transaction_ref=response.data['reference']
                    )
                    db.add(user_subscription)

                db.commit()

                return BaseResponse(
                    statusCode=status.HTTP_200_OK,
                    message="Success",
                    data=response.data['authorization_url']
                )
                 


        except Exception as e:
            logging.error("subscribe_to_plan failed with ex: %s", e)
            return BaseResponse(
                statusCode=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Internal server error",
                data=None
            )
    
    def save_webhook_data(self, payload:dict) -> BaseResponse[str]:
        try:
            with self.get_session() as db:
                stage = payload.get('event')
                data = payload.get('data', {})
                external_customer_id = data.get('customer', {}).get('id')
                plan_id = data.get('plan', {}).get('id')
                
                #next_payment_date = data.get('next_payment_date') 
                #ref = data.get('reference')

                webhook_data = WebhookLogsModel(
                    external_customer_id = external_customer_id,
                    provider = 'paystack',
                    event = stage,
                    content = json.dumps(payload)
                )
                db.add(webhook_data)
                db.commit()

                user_plan = db.query(PlansModel).filter(
                    PlansModel.external_plan_id == f'{plan_id}').first()
                if not user_plan:
                    return BaseResponse(
                        statusCode=status.HTTP_200_OK,
                        message="Invalid plan",
                        data=None
                    )

                user_subscription = db.query(UserSubscriptionModel)\
                                    .filter(UserSubscriptionModel.external_customer_id == f'{external_customer_id}',
                                            UserSubscriptionModel.plan_id == user_plan.id).first()
                
                match stage:
                    case 'invoice.create':
                        user_subscription.stage = stage
                        next_payment_date = data.get('subscription', {}).get('next_payment_date')
                        user_subscription.next_payment_date = next_payment_date
                        reference = data.get('transaction', {}).get('reference')
                        user_subscription.external_transaction_ref = reference
                    
                    case 'invoice.payment_failed':
                        user_subscription.stage = stage
                        user_subscription.is_active = False
                    
                    case 'invoice.update':
                        user_subscription.stage = stage
                        next_payment_date = data.get('subscription', {}).get('next_payment_date')
                        user_subscription.next_payment_date = next_payment_date
                        reference = data.get('transaction', {}).get('reference')
                        user_subscription.external_transaction_ref = reference

                    case 'subscription.create':
                        user_subscription.stage = "active"
                        user_subscription.is_active = True
                        next_payment_date = data.get('next_payment_date')
                        user_subscription.next_payment_date = next_payment_date
                    
                    case 'subscription.disable':
                        user_subscription.stage = stage
                        user_subscription.is_active = False 
                        next_payment_date = data.get('next_payment_date')
                        user_subscription.next_payment_date = next_payment_date
                    
                    case 'subscription.not_renew':
                        user_subscription.stage = stage
                        next_payment_date = data.get('next_payment_date')
                        user_subscription.next_payment_date = next_payment_date
                    
                    case 'charge.success':
                        user_subscription.stage = 'active'
                        user_subscription.is_active = True
                        user_subscription.external_transaction_ref = data.get('reference')

                user_subscription.date_updated = datetime.now(timezone.utc)

                db.commit()

                return BaseResponse(
                    statusCode=status.HTTP_200_OK,
                    message="Webhook saved",
                    data=None
                )
                

        except Exception as e:
            logging.error("save_webhook_data failed with ex: %s", e)
            return BaseResponse(
                statusCode=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Internal server error",
                data=None
            )

    def handle_callback(self, txref:str, reference:str) -> BaseResponse[str]:
        try:
            with self.get_session() as db:
                transaction = self.paystack.Transaction.verify(reference=reference)
                if not transaction.status:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="Transaction not found",
                        data=None
                    )
                
                data = transaction.data
                external_customer_id = data.get('customer', {}).get('id')
                plan_id = data.get('plan_object', {}).get('id')

                user_plan = db.query(PlansModel).filter(PlansModel.external_plan_id == f'{plan_id}').first()
                if not user_plan:
                    return BaseResponse(
                        statusCode=status.HTTP_200_OK,
                        message="Invalid plan",
                        data=None
                    )

                user_subscription = db.query(UserSubscriptionModel)\
                                    .filter(UserSubscriptionModel.external_customer_id == f'{external_customer_id}',
                                            UserSubscriptionModel.plan_id == user_plan.id).first()
                
                if not user_subscription:
                    return BaseResponse(
                        statusCode=status.HTTP_200_OK,
                        message="User subscription not found",
                        data=None
                    )
                
                
                subscription_for_user_plan = paystack.Subscription.list(
                    plan=user_plan.external_plan_id,
                    customer = external_customer_id
                )

                if subscription_for_user_plan.data:
                    last_subscription = subscription_for_user_plan.data[-1]
                    if last_subscription['status'] in ['active', 'non-renewing']:
                        user_subscription.stage = last_subscription['status']
                        user_subscription.next_payment_date = last_subscription['next_payment_date']
                        user_subscription.is_active = True
                        user_subscription.external_customer_id = external_customer_id
                    else:
                        user_subscription.is_active = False
                        user_subscription.stage = last_subscription['status']
                    
                    user_subscription.date_updated = datetime.now(timezone.utc)

                    db.commit()
                    return BaseResponse(
                            statusCode=status.HTTP_200_OK,
                            message="Callback handled", #redirect to success page
                            data=None
                        )   
                    
                return BaseResponse(
                    statusCode=status.HTTP_400_BAD_REQUEST,
                    message="Callback failed", #redirect to error page 
                    data=None
                )
                

        except Exception as e:
            logging.error("handle_callback failed with ex: %s", e)
            return BaseResponse(
                statusCode=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Internal server error",
                data=None
            ) 

    def get_user_subscription(self, user_id:int, db) -> BaseResponse[SubscriptionResponse]:
        try:
                user = db.query(UserModel).filter(
                    UserModel.id == user_id).first()
                if not user:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="User not found",
                        data=None
                    )

                if not user.is_active:
                    return BaseResponse(
                        statusCode=status.HTTP_400_BAD_REQUEST,
                        message="User is not active",
                        data=None
                    )

                user_subscription = db.query(UserSubscriptionModel)\
                    .filter(UserSubscriptionModel.user_id == user_id,
                            UserSubscriptionModel.is_active == True).first()

                # try to fetch plan external

                if not user_subscription or not user_subscription.is_active:
                    return BaseResponse(
                        statusCode=status.HTTP_200_OK,
                        message="User subscription not found",
                        data=SubscriptionResponse(plan_id=0, plan_name="Free")
                    )

                plan = db.query(PlansModel).filter(
                    PlansModel.id == user_subscription.plan_id).first()
                return BaseResponse(
                    statusCode=status.HTTP_200_OK,
                    message="User subscription not found",
                    data=SubscriptionResponse(
                        plan_id=plan.id, plan_name=plan.readable_name)
                )

        except Exception as e:
            logging.error("get_user_subscription failed with ex: %s", e)
            return BaseResponse(
                        statusCode=status.HTTP_200_OK,
                        message="User subscription not found",
                        data=SubscriptionResponse(plan_id=0, plan_name="Free")
                    )
