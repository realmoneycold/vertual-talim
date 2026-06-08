from aiogram import Router

def get_handlers_router() -> Router:
    from .start import router as start_router
    from .admin import router as admin_router
    from .courses import router as courses_router
    
    main_router = Router()
    main_router.include_routers(
        admin_router,
        start_router,
        courses_router
    )
    return main_router
