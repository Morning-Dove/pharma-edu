from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from database import get_db
from exceptions import PatientNotFound
from models import Patient, Prescription
from schemas import (
    PatientBasicInfo,
    PatientDetailedInfo,
    PatientCreateRequest,
    PatientCreateResponse,
    PatientRxHistoryItem,
    PatientUpdateRequest
)

router = APIRouter()


@router.get("/patients")
async def get_patients(session: Session = Depends(get_db)) -> list[PatientBasicInfo]:
    return session.exec(select(Patient.id, Patient.first_name, Patient.last_name, Patient.date_of_birth)).all()


@router.get("/patients/{patient_id}")
async def get_patient(patient_id: int, session: Session = Depends(get_db)) -> PatientDetailedInfo:
    patient: Patient | None = session.get(Patient, patient_id)
    if patient is None:
        raise PatientNotFound(id=patient_id)

    def convert_to_prescription_history(prescription: Prescription) -> PatientRxHistoryItem:
        return PatientRxHistoryItem(
            rx_number=prescription.rx_number,
            prescriber_id=prescription.prescriber_id,
            prescriber_first_name=prescription.prescriber.first_name,
            prescriber_last_name=prescription.prescriber.last_name,
            prescriber_type=prescription.prescriber.prescriber_type,
            prescribed_date=prescription.prescribed_date,
            prescription_status=prescription.status,
            rx_item_name=prescription.rx_item.name,
            rx_item_strength=prescription.rx_item.strength,
            quantity=prescription.quantity,
            refills=prescription.refills,
            directions=prescription.directions,
        )

    detailed_info = patient.model_dump(exclude=['prescriptions'])
    detailed_info["prescriptions"] = map(convert_to_prescription_history, patient.prescriptions)
    return PatientDetailedInfo(**detailed_info)


@router.post("/patients")
async def create_patient(patient_create_request: PatientCreateRequest, session: Session = Depends(get_db)) -> PatientCreateResponse:
    patient: Patient = Patient.from_orm(patient_create_request)
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return PatientCreateResponse(patient_id=patient.id)


@router.patch("/patients/{patient_id}")
async def update_patient(patient_id: int, patient_update: PatientUpdateRequest, session: Session = Depends(get_db)):
    """ Update specific fields of a patient, but the patient needs to exist. All fields are optional. """
    patient: Patient | None = session.get(Patient, patient_id)
    if patient is None:
        raise PatientNotFound(id=patient_id)

    for attr, value in patient_update.model_dump(exclude_unset=True).items():
        setattr(patient, attr, value)

    session.add(patient)
    session.commit()
    session.refresh(patient)
    # TODO: Return a 204 or whatever


@router.delete("/patients/{patient_id}")
async def delete_patient(patient_id: int, session: Session = Depends(get_db)):
    patient: Patient | None = session.get(Patient, patient_id)
    if patient is None:
        raise PatientNotFound(id=patient_id)
    for prescription in patient.prescriptions:
        session.delete(prescription)
    session.delete(patient)
    session.commit()