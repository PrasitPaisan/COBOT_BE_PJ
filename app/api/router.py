from fastapi import APIRouter

from app.api.routes import auth, camera, debug, inventory, machine, prescription, task, tray

api_router = APIRouter()
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(debug.router, tags=["debug"])
api_router.include_router(machine.router, tags=["machine"])
api_router.include_router(camera.router, tags=["camera"])
api_router.include_router(inventory.router, tags=["inventory"])
api_router.include_router(prescription.router, tags=["prescription"])
api_router.include_router(task.router, tags=["task"])
api_router.include_router(tray.router, tags=["tray"])
