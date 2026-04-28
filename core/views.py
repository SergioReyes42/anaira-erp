from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from .models import Company, AIQueryLog, AIActionDraft, UserSessionLog
from django.db import transaction
from django.contrib.auth.models import Group
from django.urls import reverse
from django.shortcuts import redirect
from django.http import JsonResponse
import json
from .ai_brain import responder_chat_contable, ejecutar_tool_contable
from django.utils import timezone
import decimal
from accounting.models import JournalEntry, JournalEntryLine, Account

User = get_user_model()

# --- 1. LANDING Y DASHBOARD ---
def landing(request):
    """Página de bienvenida pública"""
    if request.user.is_authenticated:
        return redirect('core:home')
    return render(request, 'core/landing.html')

@login_required
def home(request):
    """Dashboard Principal"""
    return render(request, 'core/home.html')

# --- 2. GESTIÓN DE EMPRESAS ---
@login_required
def select_company(request):
    """Fase 2 del Login: Selector Original (Muestra todas las empresas)"""
    
    if request.method == 'POST':
        company_id = request.POST.get('company_id')
        if company_id:
            company = get_object_or_404(Company, id=company_id)
            
            # Asignamos la empresa a la variable de memoria del usuario
            request.user.current_company = company
            
            try:
                request.user.save()
            except Exception:
                pass # Ignoramos si el usuario nativo rechaza el guardado
                
            return redirect('core:home')

    # Versión estable: listamos todas las empresas para que elija
    companies = Company.objects.all() 
    
    return render(request, 'core/select_company.html', {'companies': companies})

@login_required
def company_list(request):
    """Lista de empresas"""
    companies = Company.objects.all()
    return render(request, 'core/company_list.html', {'companies': companies})

@login_required
def company_create(request):
    """Crear nueva empresa"""
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Company.objects.create(name=name)
            messages.success(request, "Empresa creada.")
            return redirect('company_list')
    return render(request, 'core/company_form.html')

# --- 3. USUARIOS Y PERFIL ---
def register(request):
    """Registro de usuarios"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Cuenta creada. Inicia sesión.")
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def profile_view(request):
    """Ver perfil del usuario"""
    return render(request, 'core/profile.html', {'user': request.user})

@login_required
def user_list(request):
    """Lista de usuarios"""
    return render(request, 'core/user_list.html')

@login_required
def user_create(request):
    """Crear usuario (Aquí estaba el error, ya la agregamos)"""
    if request.method == 'POST':
        # Aquí iría la lógica de creación
        return redirect('user_list')
    return render(request, 'core/user_form.html')

# --- 4. EXTRAS ---
@login_required
def system_panel(request):
    """VISTA ADMIN: Centro de Mando para gestión de usuarios y sistema"""
    
    es_admin = request.user.is_superuser or request.user.groups.filter(name='Administrador').exists()
    
    if not es_admin:
        messages.error(request, "⛔ Acceso denegado. Esta área es exclusiva para Administradores del Sistema.")
        return redirect('core:home')

    # 🔥 NUEVO: Atrapamos el formulario de creación de usuario
    if request.method == 'POST' and 'create_user' in request.POST:
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        rol_nombre = request.POST.get('rol')

        try:
            with transaction.atomic():
                # 1. Magia de Django: Crea el usuario y ENCRIPTA la contraseña
                nuevo_usuario = User.objects.create_user(
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    password=password
                )
                
                # 2. Le asignamos la misma empresa que tiene el Administrador que lo está creando
                if hasattr(nuevo_usuario, 'current_company'):
                    nuevo_usuario.current_company = request.user.current_company
                    nuevo_usuario.save()

                # 3. Le asignamos su Puesto/Rol (Piloto, Contadora, etc.)
                if rol_nombre:
                    # Buscamos el grupo, si no existe, lo crea automáticamente
                    grupo, created = Group.objects.get_or_create(name=rol_nombre)
                    nuevo_usuario.groups.add(grupo)

                messages.success(request, f"✅ ¡Usuario '{username}' creado exitosamente como {rol_nombre}!")
                return redirect('core:system_panel')

        except Exception as e:
            messages.error(request, f"❌ Error al crear usuario. Revisa que el nombre de usuario no exista ya. Detalle: {str(e)}")
            return redirect('core:system_panel')

    # Traemos todos los usuarios y todos los grupos disponibles para el formulario
    usuarios = User.objects.all().prefetch_related('groups').order_by('-date_joined')
    grupos_disponibles = Group.objects.all()
    
    return render(request, 'core/system_panel.html', {
        'usuarios': usuarios,
        'grupos_disponibles': grupos_disponibles,
    })

def db_fix_view(request):
    """Vista de reparación de emergencia"""
    return redirect('home')

@login_required
def switch_company(request, company_id):
    """Cambia la sucursal activa del usuario y recarga la página con validación de permisos."""
    company = get_object_or_404(Company, id=company_id)

    user = request.user
    allowed = (
        user.is_superuser
        or user.groups.filter(name__in=['Gerente', 'Administrador']).exists()
        or user.allowed_companies.filter(id=company.id).exists()
    )

    if not allowed:
        messages.error(request, "⛔ No tienes permisos para cambiar a esa empresa.")
        next_url = request.META.get('HTTP_REFERER', '/')
        return redirect(next_url)

    user.current_company = company
    user.save(update_fields=['current_company'])
    request.session['company_id'] = company.id

    messages.success(request, f"🏢 Cambio exitoso: Ahora estás operando en {company.name}")

    next_url = request.META.get('HTTP_REFERER', '/')
    return redirect(next_url)

@login_required
def reporting_hub(request):
    """Hub central de reportes exportables por módulo"""
    reports_by_module = [
        {
            "module": "Contabilidad",
            "icon": "bi-journal-text",
            "reports": [
                {
                    "name": "Libro Diario General",
                    "view_url": reverse("accounting:general_journal"),
                    "excel_url": reverse("accounting:export_general_journal_excel"),
                    "pdf_url": reverse("accounting:export_general_journal_pdf"),
                    "description": "Movimientos contables con exportación en Excel y PDF.",
                }
            ],
        },
        {
            "module": "Ventas",
            "icon": "bi-cart-check",
            "reports": [],
        },
        {
            "module": "Inventario",
            "icon": "bi-box-seam",
            "reports": [],
        },
        {
            "module": "RRHH",
            "icon": "bi-people",
            "reports": [],
        },
        {
            "module": "Importaciones",
            "icon": "bi-ship",
            "reports": [],
        },
    ]
    return render(request, "core/reporting_hub.html", {"reports_by_module": reports_by_module})


@login_required
def login_router(request):
    """
    Enrutador Inteligente post-login:
    - Si es Superusuario, lo manda al Dashboard (con selector habilitado arriba).
    - Si es usuario normal, le asigna su sucursal fija y lo manda al Dashboard.
    """
    user = request.user
    
    # 1. Si es Administrador/Gerente
    if user.is_superuser or user.groups.filter(name__in=['Gerente', 'Administrador']).exists():
        # Asignamos la Sede Central por defecto si no tiene una activa
        if not user.current_company:
            pass
        return redirect('home')
        
    # 2. Si es un usuario normal (Ventas, Bodega, etc.)
    else:
        if hasattr(user, 'assigned_company') and user.assigned_company:
            user.current_company = user.assigned_company
            user.save()
            
        return redirect('home')

@login_required
def ai_contable_chat_page(request):
    """Página UI del chat IA contable (Fase 1)."""
    return render(request, "core/ai_contable_chat.html")


@login_required
def ai_accounting_chat(request):
    """Endpoint JSON para chat IA contable (Fase 2: tools + auditoría)."""
    if request.method != 'POST':
        return JsonResponse({"ok": False, "error": "Método no permitido."}, status=405)

    pregunta = (request.POST.get('pregunta') or '').strip()
    payload_raw = (request.POST.get('payload') or '').strip()

    if not pregunta:
        return JsonResponse({"ok": False, "error": "La pregunta está vacía."}, status=400)

    company = getattr(request.user, 'current_company', None)
    if not company:
        return JsonResponse({"ok": False, "error": "No tienes empresa activa."}, status=400)

    allowed_roles = ['Contadora', 'Auxiliar Contable', 'Gerente', 'Administrador']
    allowed = request.user.is_superuser or request.user.groups.filter(name__in=allowed_roles).exists()
    if not allowed:
        AIQueryLog.objects.create(
            user=request.user,
            company=company,
            question=pregunta,
            tool_name='blocked',
            request_payload={},
            response_payload={"error": "Sin permisos"},
            status='BLOCKED'
        )
        return JsonResponse({"ok": False, "error": "No tienes permisos para usar IA contable avanzada."}, status=403)

    payload = {}
    if payload_raw:
        try:
            payload = json.loads(payload_raw)
            if not isinstance(payload, dict):
                payload = {}
        except Exception:
            payload = {}

    try:
        tool_result = ejecutar_tool_contable(pregunta, company, payload=payload)
        tool_name = tool_result.get('tool', 'chat_general')

        if tool_name == 'chat_general':
            contexto_empresa = getattr(company, 'name', None)
            chat = responder_chat_contable(pregunta, contexto_empresa=contexto_empresa)
            respuesta = {
                "ok": True,
                "tool": "chat_general",
                "resumen": chat.get("respuesta", ""),
                "data": {}
            }
        else:
            respuesta = tool_result

        AIQueryLog.objects.create(
            user=request.user,
            company=company,
            question=pregunta,
            tool_name=respuesta.get('tool', ''),
            request_payload=payload,
            response_payload=respuesta,
            status='OK' if respuesta.get('ok') else 'ERROR'
        )
        return JsonResponse(respuesta)

    except Exception as e:
        error_payload = {"ok": False, "error": f"Error interno IA: {str(e)}"}
        AIQueryLog.objects.create(
            user=request.user,
            company=company,
            question=pregunta,
            tool_name='internal_error',
            request_payload=payload,
            response_payload=error_payload,
            status='ERROR'
        )
        return JsonResponse(error_payload, status=500)


@login_required
def ai_accounting_logs(request):
    """Endpoint para ver últimos logs de IA contable."""
    if request.method != 'GET':
        return JsonResponse({"ok": False, "error": "Método no permitido."}, status=405)

    allowed_roles = ['Contadora', 'Auxiliar Contable', 'Gerente', 'Administrador']
    allowed = request.user.is_superuser or request.user.groups.filter(name__in=allowed_roles).exists()
    if not allowed:
        return JsonResponse({"ok": False, "error": "No autorizado."}, status=403)

    company = getattr(request.user, 'current_company', None)
    logs = AIQueryLog.objects.all().order_by('-created_at')
    if company:
        logs = logs.filter(company=company)

    data = []
    for l in logs[:50]:
        data.append({
            "id": l.id,
            "question": l.question,
            "tool_name": l.tool_name,
            "status": l.status,
            "created_at": l.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        })

    return JsonResponse({"ok": True, "logs": data})


def _ai_roles_allowed(user):
    allowed_roles = ['Contadora', 'Auxiliar Contable', 'Gerente', 'Administrador']
    return user.is_superuser or user.groups.filter(name__in=allowed_roles).exists()


@login_required
def ai_draft_create(request):
    if request.method != 'POST':
        return JsonResponse({"ok": False, "error": "Método no permitido."}, status=405)

    if not _ai_roles_allowed(request.user):
        return JsonResponse({"ok": False, "error": "No autorizado."}, status=403)

    company = getattr(request.user, 'current_company', None)
    if not company:
        return JsonResponse({"ok": False, "error": "No tienes empresa activa."}, status=400)

    payload_raw = (request.POST.get('payload') or '').strip()
    if not payload_raw:
        return JsonResponse({"ok": False, "error": "Payload requerido."}, status=400)

    try:
        payload = json.loads(payload_raw)
    except Exception:
        return JsonResponse({"ok": False, "error": "Payload JSON inválido."}, status=400)

    draft = AIActionDraft.objects.create(
        company=company,
        created_by=request.user,
        action_type='JOURNAL_ENTRY_DRAFT',
        draft_payload=payload,
        status='PENDING'
    )

    AIQueryLog.objects.create(
        user=request.user,
        company=company,
        question='Crear draft IA',
        tool_name='draft_create',
        request_payload=payload,
        response_payload={"draft_id": draft.id, "status": draft.status},
        status='OK'
    )
    return JsonResponse({"ok": True, "draft_id": draft.id, "status": draft.status})


@login_required
def ai_drafts_list(request):
    if request.method != 'GET':
        return JsonResponse({"ok": False, "error": "Método no permitido."}, status=405)

    if not _ai_roles_allowed(request.user):
        return JsonResponse({"ok": False, "error": "No autorizado."}, status=403)

    company = getattr(request.user, 'current_company', None)
    qs = AIActionDraft.objects.all().order_by('-created_at')
    if company:
        qs = qs.filter(company=company)

    data = []
    for d in qs[:100]:
        data.append({
            "id": d.id,
            "status": d.status,
            "action_type": d.action_type,
            "created_by": d.created_by.username,
            "created_at": d.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "approved_by": d.approved_by.username if d.approved_by else None,
            "applied_by": d.applied_by.username if d.applied_by else None,
            "rejection_reason": d.rejection_reason,
            "payload": d.draft_payload,
        })

    return JsonResponse({"ok": True, "drafts": data})


@login_required
def ai_draft_approve(request, draft_id):
    if request.method != 'POST':
        return JsonResponse({"ok": False, "error": "Método no permitido."}, status=405)

    if not _ai_roles_allowed(request.user):
        return JsonResponse({"ok": False, "error": "No autorizado."}, status=403)

    draft = get_object_or_404(AIActionDraft, id=draft_id)

    if draft.status != 'PENDING':
        return JsonResponse({"ok": False, "error": "Solo se aprueban drafts pendientes."}, status=400)

    draft.status = 'APPROVED'
    draft.approved_by = request.user
    draft.approved_at = timezone.now()
    draft.save(update_fields=['status', 'approved_by', 'approved_at'])

    return JsonResponse({"ok": True, "draft_id": draft.id, "status": draft.status})


@login_required
def ai_draft_reject(request, draft_id):
    if request.method != 'POST':
        return JsonResponse({"ok": False, "error": "Método no permitido."}, status=405)

    if not _ai_roles_allowed(request.user):
        return JsonResponse({"ok": False, "error": "No autorizado."}, status=403)

    draft = get_object_or_404(AIActionDraft, id=draft_id)

    if draft.status not in ['PENDING', 'APPROVED']:
        return JsonResponse({"ok": False, "error": "No se puede rechazar en su estado actual."}, status=400)

    reason = (request.POST.get('reason') or '').strip()
    draft.status = 'REJECTED'
    draft.rejection_reason = reason
    draft.save(update_fields=['status', 'rejection_reason'])

    return JsonResponse({"ok": True, "draft_id": draft.id, "status": draft.status})


@login_required
def ai_draft_apply(request, draft_id):
    if request.method != 'POST':
        return JsonResponse({"ok": False, "error": "Método no permitido."}, status=405)

    if not _ai_roles_allowed(request.user):
        return JsonResponse({"ok": False, "error": "No autorizado."}, status=403)

    draft = get_object_or_404(AIActionDraft, id=draft_id)

    if draft.status != 'APPROVED':
        return JsonResponse({"ok": False, "error": "Solo se pueden aplicar drafts aprobados."}, status=400)

    if draft.created_by_id == request.user.id:
        return JsonResponse({"ok": False, "error": "Segregación: quien crea no puede aplicar."}, status=403)

    payload = draft.draft_payload or {}
    concept = (payload.get('concepto') or '').strip()
    lineas = payload.get('lineas') or []
    fecha = payload.get('fecha')

    if not concept or not isinstance(lineas, list) or not lineas:
        return JsonResponse({"ok": False, "error": "Draft inválido: falta concepto o líneas."}, status=400)

    total_debe = decimal.Decimal('0.00')
    total_haber = decimal.Decimal('0.00')
    lineas_ok = []

    for ln in lineas:
        account_id = ln.get('account_id')
        try:
            account = Account.objects.get(id=account_id, is_transactional=True)
            debit = decimal.Decimal(str(ln.get('debit', 0)))
            credit = decimal.Decimal(str(ln.get('credit', 0)))
        except Exception:
            return JsonResponse({"ok": False, "error": "Línea inválida en draft."}, status=400)

        if debit < 0 or credit < 0 or (debit > 0 and credit > 0) or (debit == 0 and credit == 0):
            return JsonResponse({"ok": False, "error": "Línea contable inválida (Debe/Haber)."}, status=400)

        total_debe += debit
        total_haber += credit
        lineas_ok.append((account, debit, credit))

    if total_debe != total_haber:
        return JsonResponse({"ok": False, "error": "Partida descuadrada: Debe debe ser igual a Haber."}, status=400)

    company = getattr(request.user, 'current_company', None)
    company_key = str(getattr(company, 'id', company)) if company else None

    with transaction.atomic():
        entry = JournalEntry.objects.create(
            date=fecha or timezone.now().date(),
            concept=concept,
            company=company_key,
            is_opening_balance=False
        )

        for account, debit, credit in lineas_ok:
            JournalEntryLine.objects.create(
                entry=entry,
                account=account,
                debit=debit,
                credit=credit
            )

        draft.status = 'APPLIED'
        draft.applied_by = request.user
        draft.applied_at = timezone.now()
        draft.save(update_fields=['status', 'applied_by', 'applied_at'])

    AIQueryLog.objects.create(
        user=request.user,
        company=company,
        question='Aplicar draft IA',
        tool_name='draft_apply',
        request_payload={"draft_id": draft.id},
        response_payload={"entry_id": entry.id, "status": "APPLIED"},
        status='OK'
    )

    return JsonResponse({"ok": True, "draft_id": draft.id, "status": draft.status, "entry_id": entry.id})


@login_required
def user_activity_dashboard(request):
    allowed = request.user.is_superuser or request.user.groups.filter(name__in=['Gerente', 'Administrador']).exists()
    if not allowed:
        messages.error(request, "⛔ No autorizado para ver actividad de usuarios.")
        return redirect('core:home')

    now = timezone.now()
    threshold = now - timezone.timedelta(minutes=5)

    online_logs = UserSessionLog.objects.filter(
        logout_at__isnull=True,
        last_seen__gte=threshold
    ).select_related('user', 'company').order_by('-last_seen')

    recent_logins = UserSessionLog.objects.select_related('user', 'company').order_by('-login_at')[:100]

    context = {
        'online_logs': online_logs,
        'recent_logins': recent_logins,
        'online_count': online_logs.count(),
    }
    return render(request, 'core/user_activity_dashboard.html', context)


def set_working_period(request):
    """Guarda el mes y año en el que el usuario quiere trabajar"""
    if request.method == 'POST':
        mes = request.POST.get('working_month')
        anio = request.POST.get('working_year')
        
        # Lo guardamos en la memoria de la sesión
        if mes and anio:
            request.session['working_month'] = int(mes)
            request.session['working_year'] = int(anio)
            messages.success(request, f"🗓️ Período de trabajo cambiado a {mes}/{anio}.")
            
    # Lo regresamos a la pantalla donde estaba
    return redirect(request.META.get('HTTP_REFERER', '/'))
