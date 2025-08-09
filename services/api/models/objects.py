from pydantic import BaseModel, ConfigDict, Field, PrivateAttr
from typing import Optional, Dict
from datetime import datetime


class PatientRecord(BaseModel):
    # patient_id: int
    # name: str
    # surname: str
    age: int = Field(..., gt=0, description="Age must be a positive number")
    height: float = Field(..., gt=0, description="Height must be a positive number in meters")
    weight: float = Field(..., gt=0, description="Weight must be a positive number in kilograms")
    resent_surgery: bool
    chronic_pain: bool
    _bmi: float = PrivateAttr()
    _recommendation: Optional[str] = PrivateAttr()

    model_config = ConfigDict(validate_assignment=True)

    def model_post_init(self, __context):
        self._bmi = round(self.weight / (self.height ** 2), 2)
        self._recommendation = self._generate_recommendation()

    @property
    def bmi(self) -> float:
        """Public getter for BMI."""
        return self._bmi

    @property
    def recommendation(self) -> Optional[str]:
        """Public getter for the clinical recommendation."""
        return self._recommendation

    def _generate_recommendation(self) -> Optional[str]:
        """
        Mock AI model: Rule-based clinical recommendation.
        Future: replace with real AI logic.
        """
        if self.age > 65 and self.chronic_pain:
            return "Physical Therapy"
        if self.bmi > 30:
            return "Weight Management Program"
        if self.resent_surgery:
            return "Post-Op Rehabilitation Plan"
        return None

    def as_dict(self, patient_id: int) -> Dict:
        return {
            "patient_id": patient_id,
            "age": self.age,
            "height": self.height,
            "weight": self.weight,
            "resent_surgery": self.resent_surgery,
            "chronic_pain": self.chronic_pain,
            "bmi": self.bmi,
            "recommendation": self.recommendation
        }

    def model_dump(self, *args, **kwargs):
        """Include BMI and recommendation in dumped data."""
        data = super().model_dump(*args, **kwargs)
        data["bmi"] = self.bmi
        data["recommendation"] = self.recommendation
        return data