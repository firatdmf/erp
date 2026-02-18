@login_required
@require_http_methods(["POST"])
def edit_task(request, task_id):
    """Edit a team task"""
    task = get_object_or_404(TeamTask, id=task_id)
    
    # Check permissions (any team member can edit for now, or restrict to creator/assignee/admin)
    if not TeamMember.objects.filter(team=task.team, user=request.user).exists():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    # Update fields
    title = request.POST.get('name')
    if title:
        task.title = title
        
    priority = request.POST.get('priority')
    if priority:
        task.priority = priority
        
    due_date = request.POST.get('due_date')
    if due_date:
        task.due_date = due_date
    else:
        task.due_date = None # Handle clearing date if needed
        
    task.save()
    
    # Log history? (Optimization: Add history logging here)
    TeamTaskHistory.objects.create(
        task=task,
        user=request.user,
        event_type='status_change', # Maybe add 'edit' type later, reusing status_change or generic for now
        new_value=f"Task details updated"
    )
    
    return JsonResponse({'success': True, 'message': 'Task updated successfully'})
