from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database.models import Customer, Dataset


class CustomerRepository:
    """CRUD operations for customer profiles, querying, search, and segmentation."""

    @staticmethod
    def get_by_id(db: Session, customer_uuid: str) -> Optional[Customer]:
        return db.query(Customer).filter(Customer.id == customer_uuid).first()

    @staticmethod
    def get_by_customer_id(
        db: Session,
        customer_id: str,
        dataset_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Optional[Customer]:
        query = db.query(Customer).filter(Customer.customer_id == customer_id)
        if dataset_id:
            query = query.filter(Customer.dataset_id == dataset_id)
        if user_id:
            query = query.filter(Customer.user_id == user_id)
        return query.first()

    @staticmethod
    def create(
        db: Session,
        customer_id: str,
        customer_dict: Dict[str, Any],
        dataset_id: Optional[str] = None,
        user_id: Optional[str] = None,
        commit: bool = True,
    ) -> Customer:
        customer = Customer(
            customer_id=customer_id,
            dataset_id=dataset_id,
            user_id=user_id,
            gender=customer_dict.get("gender"),
            senior_citizen=int(customer_dict.get("SeniorCitizen", 0)),
            partner=customer_dict.get("Partner"),
            dependents=customer_dict.get("Dependents"),
            tenure=int(customer_dict.get("tenure", 0)),
            phone_service=customer_dict.get("PhoneService"),
            multiple_lines=customer_dict.get("MultipleLines"),
            internet_service=customer_dict.get("InternetService"),
            online_security=customer_dict.get("OnlineSecurity"),
            online_backup=customer_dict.get("OnlineBackup"),
            device_protection=customer_dict.get("DeviceProtection"),
            tech_support=customer_dict.get("TechSupport"),
            streaming_tv=customer_dict.get("StreamingTV"),
            streaming_movies=customer_dict.get("StreamingMovies"),
            contract=customer_dict.get("Contract"),
            paperless_billing=customer_dict.get("PaperlessBilling"),
            payment_method=customer_dict.get("PaymentMethod"),
            monthly_charges=float(customer_dict.get("MonthlyCharges", 0.0)),
            total_charges=float(customer_dict.get("TotalCharges", 0.0))
        )
        db.add(customer)
        if commit:
            db.commit()
            db.refresh(customer)
        else:
            db.flush()
        return customer

    @staticmethod
    def bulk_create(
        db: Session,
        customers_data: List[Dict[str, Any]],
        dataset_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[Customer]:
        customer_objs = []
        for d in customers_data:
            cust = Customer(
                customer_id=d.get("customer_id") or d.get("customerID") or "UNKNOWN",
                dataset_id=dataset_id,
                user_id=user_id,
                gender=d.get("gender"),
                senior_citizen=int(d.get("SeniorCitizen", 0)),
                partner=d.get("Partner"),
                dependents=d.get("Dependents"),
                tenure=int(d.get("tenure", 0)),
                phone_service=d.get("PhoneService"),
                multiple_lines=d.get("MultipleLines"),
                internet_service=d.get("InternetService"),
                online_security=d.get("OnlineSecurity"),
                online_backup=d.get("OnlineBackup"),
                device_protection=d.get("DeviceProtection"),
                tech_support=d.get("TechSupport"),
                streaming_tv=d.get("StreamingTV"),
                streaming_movies=d.get("StreamingMovies"),
                contract=d.get("Contract"),
                paperless_billing=d.get("PaperlessBilling"),
                payment_method=d.get("PaymentMethod"),
                monthly_charges=float(d.get("MonthlyCharges", 0.0)),
                total_charges=float(d.get("TotalCharges", 0.0))
            )
            customer_objs.append(cust)

        db.bulk_save_objects(customer_objs, return_defaults=True)
        db.commit()
        return customer_objs

    @staticmethod
    def search_customers(
        db: Session,
        search_term: Optional[str] = None,
        dataset_id: Optional[str] = None,
        user_id: Optional[str] = None,
        contract: Optional[str] = None,
        internet_service: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Customer], int]:
        query = db.query(Customer)

        if dataset_id:
            query = query.filter(Customer.dataset_id == dataset_id)

        if user_id:
            query = query.filter(Customer.user_id == user_id)

        if search_term:
            query = query.filter(
                or_(
                    Customer.customer_id.ilike(f"%{search_term}%"),
                    Customer.contract.ilike(f"%{search_term}%"),
                    Customer.payment_method.ilike(f"%{search_term}%")
                )
            )

        if contract:
            query = query.filter(Customer.contract == contract)

        if internet_service:
            query = query.filter(Customer.internet_service == internet_service)

        total = query.count()
        customers = query.order_by(Customer.created_at.desc()).offset(offset).limit(limit).all()
        return customers, total
