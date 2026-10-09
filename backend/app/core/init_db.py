from app.models.assessment import Base
import app.models.attack_surface
import app.models.compliance
import app.models.remediation
import app.models.retest
import app.models.report
from app.core.database import engine

def init_db():
    Base.metadata.create_all(bind=engine)

