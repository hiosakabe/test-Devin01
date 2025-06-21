from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.urls import reverse
from django.http import JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils.text import slugify
from .models import (
    QuizCategory, QuizQuestion, QuizAnswer, QuizResult, QuizSession, QuizParticipant,
    KnowledgeCategory, KnowledgeArticle, KnowledgeTag, KnowledgeComment, 
    KnowledgeBookmark, KnowledgeView, KnowledgeRevision
)
from .forms import (
    PlayerNameForm, QuizAnswerForm, QuizSessionForm, JoinSessionForm,
    KnowledgeArticleForm, KnowledgeCategoryForm, KnowledgeTagForm, 
    KnowledgeCommentForm, KnowledgeSearchForm
)
from .utils import enhance_content_for_display, extract_text_preview
import json

def index(request):
    context = {
        'current_time': timezone.now(),
    }
    return render(request, 'sample_app/index.html', context)

def quiz_start(request):
    if request.method == 'POST':
        form = PlayerNameForm(request.POST)
        if form.is_valid():
            player_name = form.cleaned_data['player_name']
            category = form.cleaned_data['category']
            
            # セッションに情報を保存
            request.session['player_name'] = player_name
            request.session['category_id'] = category.id
            request.session['current_question'] = 0
            request.session['correct_answers'] = 0
            request.session['total_questions'] = 5  # 出題する問題数
            
            return redirect('quiz_question')
    else:
        form = PlayerNameForm()
    
    return render(request, 'sample_app/quiz_start.html', {'form': form})

def quiz_question(request):
    # セッションから情報を取得
    player_name = request.session.get('player_name')
    category_id = request.session.get('category_id')
    current_question = request.session.get('current_question', 0)
    total_questions = request.session.get('total_questions', 5)
    
    if not player_name or current_question >= total_questions:
        return redirect('quiz_result')
    
    # カテゴリーに基づいて問題を取得
    questions = QuizQuestion.objects.filter(category_id=category_id)
    
    if current_question >= questions.count():
        return redirect('quiz_result')
    
    question = questions[current_question]
    
    if request.method == 'POST':
        form = QuizAnswerForm(request.POST, question=question)
        if form.is_valid():
            answer_id = form.cleaned_data['answer']
            answer = QuizAnswer.objects.get(id=answer_id)
            
            if answer.is_correct:
                request.session['correct_answers'] = request.session.get('correct_answers', 0) + 1
            
            request.session['current_question'] = current_question + 1
            return redirect('quiz_question')
    else:
        form = QuizAnswerForm(question=question)
    
    progress = int((current_question / total_questions) * 100)
    
    context = {
        'player_name': player_name,
        'question': question,
        'form': form,
        'current_question': current_question + 1,
        'total_questions': total_questions,
        'progress': progress,
    }
    
    return render(request, 'sample_app/quiz_question.html', context)

def quiz_result(request):
    player_name = request.session.get('player_name')
    category_id = request.session.get('category_id')
    correct_answers = request.session.get('correct_answers', 0)
    total_questions = request.session.get('total_questions', 5)
    
    if not player_name:
        return redirect('quiz_start')
    
    category = QuizCategory.objects.get(id=category_id)
    
    # 結果を保存
    result = QuizResult(
        player_name=player_name,
        score=correct_answers,
    )
    result.save()
    
    # セッションをクリア
    for key in ['player_name', 'category_id', 'current_question', 'correct_answers', 'total_questions']:
        if key in request.session:
            del request.session[key]
    
    context = {
        'player_name': player_name,
        'category': category,
        'correct_answers': correct_answers,
        'total_questions': total_questions,
        'percentage': int((correct_answers / total_questions) * 100),
    }
    
    return render(request, 'sample_app/quiz_result.html', context)

def quiz_host(request):
    """クイズマスターのホスト画面"""
    if request.method == 'POST':
        form = QuizSessionForm(request.POST)
        if form.is_valid():
            quiz_master = form.cleaned_data['quiz_master']
            category = form.cleaned_data['category']
            total_questions = form.cleaned_data['total_questions']
            
            # セッションを作成
            session = QuizSession(
                quiz_master=quiz_master,
                category=category,
                total_questions=total_questions
            )
            session.save()
            
            return redirect('quiz_session', session_id=session.session_id)
    else:
        form = QuizSessionForm()
    
    return render(request, 'sample_app/quiz_host.html', {'form': form})

def quiz_join(request):
    """参加者のセッション参加画面"""
    if request.method == 'POST':
        form = JoinSessionForm(request.POST)
        if form.is_valid():
            session_id = form.cleaned_data['session_id']
            player_name = form.cleaned_data['player_name']
            
            try:
                session = QuizSession.objects.get(session_id=session_id)
                
                # 参加者を追加
                participant = QuizParticipant(
                    session=session,
                    name=player_name
                )
                participant.save()
                
                return redirect('quiz_session', session_id=session.session_id)
            except QuizSession.DoesNotExist:
                form.add_error('session_id', '指定されたセッションIDは存在しません。')
    else:
        form = JoinSessionForm()
    
    return render(request, 'sample_app/quiz_join.html', {'form': form})

def quiz_session(request, session_id):
    """クイズセッション画面"""
    try:
        session = QuizSession.objects.get(session_id=session_id)
        participants = session.participants.all()
        
        # クイズマスターかどうかを判定
        is_quiz_master = request.GET.get('name') == session.quiz_master
        
        context = {
            'session': session,
            'participants': participants,
            'is_quiz_master': is_quiz_master,
        }
        
        return render(request, 'sample_app/quiz_session.html', context)
    except QuizSession.DoesNotExist:
        return redirect('index')

@csrf_exempt
def quiz_api(request, session_id):
    """クイズAPIエンドポイント"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            session = QuizSession.objects.get(session_id=session_id)
            
            if action == 'get_question':
                question_index = data.get('question_index')
                questions = QuizQuestion.objects.filter(category=session.category)
                
                if question_index < questions.count():
                    question = questions[question_index]
                    answers = question.answers.all()
                    
                    return JsonResponse({
                        'id': question.id,
                        'text': question.question_text,
                        'answers': [{'id': answer.id, 'text': answer.answer_text} for answer in answers]
                    })
                else:
                    return JsonResponse({'error': '質問が見つかりません。'}, status=404)
            
            elif action == 'submit_answer':
                participant_name = data.get('name')
                answer_id = data.get('answer_id')
                
                answer = QuizAnswer.objects.get(id=answer_id)
                is_correct = answer.is_correct
                
                if is_correct:
                    participant = QuizParticipant.objects.get(session=session, name=participant_name)
                    participant.score += 1
                    participant.save()
                
                return JsonResponse({'is_correct': is_correct})
            
            elif action == 'end_session':
                session.status = 'completed'
                session.save()
                
                participants = session.participants.all().order_by('-score')
                results = [{'name': p.name, 'score': p.score} for p in participants]
                
                return JsonResponse({'results': results})
            
            else:
                return JsonResponse({'error': '不明なアクション。'}, status=400)
        
        except QuizSession.DoesNotExist:
            return JsonResponse({'error': 'セッションが見つかりません。'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'POSTリクエストのみ許可されています。'}, status=405)


def knowledge_home(request):
    """Knowledge system home page"""
    recent_articles = KnowledgeArticle.objects.filter(status='published').order_by('-updated_at')[:6]
    featured_articles = KnowledgeArticle.objects.filter(status='published', featured=True)[:3]
    categories = KnowledgeCategory.objects.annotate(article_count=Count('articles')).order_by('name')
    popular_tags = KnowledgeTag.objects.annotate(article_count=Count('articles')).order_by('-article_count')[:10]
    
    context = {
        'recent_articles': recent_articles,
        'featured_articles': featured_articles,
        'categories': categories,
        'popular_tags': popular_tags,
    }
    return render(request, 'sample_app/knowledge_home.html', context)


def knowledge_search(request):
    """Advanced search page for knowledge articles"""
    from django.contrib.auth.models import User
    
    categories = KnowledgeCategory.objects.all().order_by('name')
    authors = User.objects.filter(knowledgearticle__isnull=False).distinct().order_by('username')
    popular_tags = KnowledgeTag.objects.annotate(article_count=Count('articles')).order_by('-article_count')[:20]
    
    search_performed = bool(request.GET.get('query') or request.GET.get('category') or 
                           request.GET.get('tags') or request.GET.get('author') or 
                           request.GET.get('date_from') or request.GET.get('date_to'))
    
    articles = KnowledgeArticle.objects.none()
    page_obj = None
    total_results = 0
    
    if search_performed:
        articles = KnowledgeArticle.objects.filter(status='published').select_related('category', 'author').prefetch_related('tags')
        
        query = request.GET.get('query', '').strip()
        category_id = request.GET.get('category')
        tag_ids = request.GET.getlist('tags')
        author_id = request.GET.get('author')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        if query:
            search_terms = query.split()
            search_query = Q()
            
            for term in search_terms:
                term_query = (
                    Q(title__icontains=term) | 
                    Q(content__icontains=term) | 
                    Q(summary__icontains=term) |
                    Q(tags__name__icontains=term) |
                    Q(category__name__icontains=term)
                )
                search_query &= term_query
            
            articles = articles.filter(search_query).distinct()
        
        if category_id:
            articles = articles.filter(category_id=category_id)
        
        if tag_ids:
            articles = articles.filter(tags__id__in=tag_ids).distinct()
        
        if author_id:
            articles = articles.filter(author_id=author_id)
        
        if date_from:
            from datetime import datetime
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                articles = articles.filter(created_at__gte=date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            from datetime import datetime
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                articles = articles.filter(created_at__lte=date_to_obj)
            except ValueError:
                pass
        
        sort_by = request.GET.get('sort', '-updated_at')
        valid_sorts = ['-updated_at', 'updated_at', '-created_at', 'created_at', 'title', '-title', '-view_count', 'view_count']
        if sort_by in valid_sorts:
            articles = articles.order_by(sort_by)
        else:
            articles = articles.order_by('-updated_at')
        
        total_results = articles.count()
        
        paginator = Paginator(articles, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
    
    popular_articles = KnowledgeArticle.objects.filter(status='published').order_by('-view_count')[:5]
    recent_articles = KnowledgeArticle.objects.filter(status='published').order_by('-updated_at')[:5]
    
    context = {
        'categories': categories,
        'authors': authors,
        'popular_tags': popular_tags,
        'search_performed': search_performed,
        'page_obj': page_obj,
        'total_results': total_results,
        'popular_articles': popular_articles,
        'recent_articles': recent_articles,
    }
    return render(request, 'sample_app/knowledge_search.html', context)


def knowledge_article_list(request):
    """List all published articles with advanced search and filtering"""
    articles = KnowledgeArticle.objects.filter(status='published').select_related('category', 'author').prefetch_related('tags')
    
    search_form = KnowledgeSearchForm(request.GET)
    search_performed = False
    
    if search_form.is_valid():
        query = search_form.cleaned_data.get('query')
        category = search_form.cleaned_data.get('category')
        tags = search_form.cleaned_data.get('tags')
        status = search_form.cleaned_data.get('status')
        author = search_form.cleaned_data.get('author')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')
        
        if any([query, category, tags, status, author, date_from, date_to]):
            search_performed = True
        
        if query:
            search_terms = query.split()
            search_query = Q()
            
            for term in search_terms:
                term_query = (
                    Q(title__icontains=term) | 
                    Q(content__icontains=term) | 
                    Q(summary__icontains=term) |
                    Q(tags__name__icontains=term) |
                    Q(category__name__icontains=term)
                )
                search_query &= term_query
            
            articles = articles.filter(search_query).distinct()
        
        if category:
            articles = articles.filter(category=category)
        
        if tags:
            articles = articles.filter(tags__in=tags).distinct()
        
        if status:
            articles = articles.filter(status=status)
        
        if author:
            articles = articles.filter(author=author)
        
        if date_from:
            articles = articles.filter(created_at__gte=date_from)
        
        if date_to:
            articles = articles.filter(created_at__lte=date_to)
    
    sort_by = request.GET.get('sort', '-updated_at')
    valid_sorts = ['-updated_at', 'updated_at', '-created_at', 'created_at', 'title', '-title', '-view_count', 'view_count']
    if sort_by in valid_sorts:
        articles = articles.order_by(sort_by)
    else:
        articles = articles.order_by('-updated_at')
    
    paginator = Paginator(articles, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'total_articles': articles.count(),
        'search_performed': search_performed,
        'current_sort': sort_by,
    }
    return render(request, 'sample_app/knowledge_article_list.html', context)


def knowledge_article_detail(request, slug):
    """Display article detail with comments"""
    article = get_object_or_404(KnowledgeArticle, slug=slug, status='published')
    
    if request.user.is_authenticated or request.META.get('REMOTE_ADDR'):
        ip_address = request.META.get('REMOTE_ADDR', '127.0.0.1')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        KnowledgeView.objects.create(
            article=article,
            user=request.user if request.user.is_authenticated else None,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        article.view_count += 1
        article.save(update_fields=['view_count'])
    
    comments = article.comments.filter(is_approved=True, parent=None).select_related('author').order_by('created_at')
    
    comment_form = KnowledgeCommentForm()
    if request.method == 'POST' and request.user.is_authenticated:
        comment_form = KnowledgeCommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.article = article
            comment.author = request.user
            comment.save()
            return redirect('knowledge_article_detail', slug=slug)
    
    is_bookmarked = False
    if request.user.is_authenticated:
        is_bookmarked = KnowledgeBookmark.objects.filter(user=request.user, article=article).exists()
    
    related_articles = KnowledgeArticle.objects.filter(
        category=article.category, 
        status='published'
    ).exclude(id=article.id)[:3]
    
    context = {
        'article': article,
        'comments': comments,
        'comment_form': comment_form,
        'is_bookmarked': is_bookmarked,
        'related_articles': related_articles,
    }
    return render(request, 'sample_app/knowledge_article_detail.html', context)


@login_required
def knowledge_article_create(request):
    """Create new knowledge article"""
    if request.method == 'POST':
        form = KnowledgeArticleForm(request.POST)
        if form.is_valid():
            try:
                article = form.save(commit=False)
                article.author = request.user
                
                if not article.slug:
                    article.slug = slugify(article.title)
                
                article.content = enhance_content_for_display(article.content)
                
                if not article.summary:
                    article.summary = extract_text_preview(article.content, 150)
                
                article.save()
                form.save_m2m()
                
                KnowledgeRevision.objects.create(
                    article=article,
                    author=request.user,
                    title=article.title,
                    content=article.content,
                    summary=article.summary,
                    change_summary="Initial creation"
                )
                
                messages.success(request, f'Article "{article.title}" has been created successfully!')
                return redirect('knowledge_article_detail', slug=article.slug)
                
            except Exception as e:
                messages.error(request, f'Error creating article: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = KnowledgeArticleForm()
    
    context = {
        'form': form,
        'action': 'Create',
    }
    return render(request, 'sample_app/knowledge_article_form.html', context)


@login_required
def knowledge_article_edit(request, slug):
    """Edit existing knowledge article"""
    article = get_object_or_404(KnowledgeArticle, slug=slug)
    
    if article.author != request.user and not request.user.is_staff:
        raise Http404("You don't have permission to edit this article")
    
    if request.method == 'POST':
        form = KnowledgeArticleForm(request.POST, instance=article)
        if form.is_valid():
            try:
                KnowledgeRevision.objects.create(
                    article=article,
                    author=request.user,
                    title=article.title,
                    content=article.content,
                    summary=article.summary,
                    change_summary=request.POST.get('change_summary', 'Updated article')
                )
                
                updated_article = form.save(commit=False)
                
                updated_article.content = enhance_content_for_display(updated_article.content)
                
                if not updated_article.summary or len(updated_article.summary.strip()) < 20:
                    updated_article.summary = extract_text_preview(updated_article.content, 150)
                
                updated_article.save()
                form.save_m2m()
                
                messages.success(request, f'Article "{updated_article.title}" has been updated successfully!')
                return redirect('knowledge_article_detail', slug=updated_article.slug)
                
            except Exception as e:
                messages.error(request, f'Error updating article: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = KnowledgeArticleForm(instance=article)
    
    context = {
        'form': form,
        'article': article,
        'action': 'Edit',
    }
    return render(request, 'sample_app/knowledge_article_form.html', context)


@login_required
def knowledge_article_delete(request, slug):
    """Delete knowledge article"""
    article = get_object_or_404(KnowledgeArticle, slug=slug)
    
    if article.author != request.user and not request.user.is_staff:
        raise Http404("You don't have permission to delete this article")
    
    if request.method == 'POST':
        article.delete()
        return redirect('knowledge_article_list')
    
    context = {
        'article': article,
    }
    return render(request, 'sample_app/knowledge_article_delete.html', context)


def knowledge_category_list(request):
    """List all knowledge categories"""
    categories = KnowledgeCategory.objects.annotate(
        article_count=Count('articles', filter=Q(articles__status='published'))
    ).order_by('name')
    
    context = {
        'categories': categories,
    }
    return render(request, 'sample_app/knowledge_category_list.html', context)


def knowledge_category_detail(request, pk):
    """Display category with its articles"""
    category = get_object_or_404(KnowledgeCategory, pk=pk)
    articles = category.articles.filter(status='published').order_by('-updated_at')
    
    paginator = Paginator(articles, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'category': category,
        'page_obj': page_obj,
    }
    return render(request, 'sample_app/knowledge_category_detail.html', context)


@login_required
def knowledge_bookmark_toggle(request, slug):
    """Toggle bookmark for an article"""
    if request.method == 'POST':
        article = get_object_or_404(KnowledgeArticle, slug=slug)
        bookmark, created = KnowledgeBookmark.objects.get_or_create(
            user=request.user,
            article=article
        )
        
        if not created:
            bookmark.delete()
            bookmarked = False
        else:
            bookmarked = True
        
        return JsonResponse({'bookmarked': bookmarked})
    
    return JsonResponse({'error': 'POST required'}, status=405)


@login_required
def knowledge_bookmarks(request):
    """List user's bookmarked articles"""
    bookmarks = KnowledgeBookmark.objects.filter(user=request.user).select_related('article').order_by('-created_at')
    
    paginator = Paginator(bookmarks, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'sample_app/knowledge_bookmarks.html', context)


@csrf_exempt
def knowledge_api(request):
    """API endpoints for knowledge system"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'search_articles':
                query = data.get('query', '')
                category_id = data.get('category_id')
                tag_ids = data.get('tag_ids', [])
                limit = min(data.get('limit', 10), 50)
                
                articles = KnowledgeArticle.objects.filter(status='published')
                
                if query:
                    search_terms = query.split()
                    search_query = Q()
                    
                    for term in search_terms:
                        term_query = (
                            Q(title__icontains=term) | 
                            Q(content__icontains=term) | 
                            Q(summary__icontains=term) |
                            Q(tags__name__icontains=term) |
                            Q(category__name__icontains=term)
                        )
                        search_query &= term_query
                    
                    articles = articles.filter(search_query).distinct()
                
                if category_id:
                    articles = articles.filter(category_id=category_id)
                
                if tag_ids:
                    articles = articles.filter(tags__id__in=tag_ids).distinct()
                
                articles = articles.select_related('category', 'author').prefetch_related('tags')[:limit]
                
                results = [{
                    'id': article.id,
                    'title': article.title,
                    'slug': article.slug,
                    'summary': article.summary,
                    'category': {
                        'id': article.category.id,
                        'name': article.category.name
                    },
                    'author': article.author.username,
                    'tags': [{'id': tag.id, 'name': tag.name, 'color': tag.color} for tag in article.tags.all()],
                    'view_count': article.view_count,
                    'updated_at': article.updated_at.isoformat()
                } for article in articles]
                
                return JsonResponse({'results': results, 'total': len(results)})
            
            elif action == 'autocomplete_search':
                query = data.get('query', '')
                if len(query) < 2:
                    return JsonResponse({'suggestions': []})
                
                articles = KnowledgeArticle.objects.filter(
                    status='published',
                    title__icontains=query
                ).values('title', 'slug')[:5]
                
                categories = KnowledgeCategory.objects.filter(
                    name__icontains=query
                ).values('name', 'id')[:3]
                
                tags = KnowledgeTag.objects.filter(
                    name__icontains=query
                ).values('name', 'id')[:3]
                
                suggestions = {
                    'articles': list(articles),
                    'categories': list(categories),
                    'tags': list(tags)
                }
                
                return JsonResponse({'suggestions': suggestions})
            
            elif action == 'get_comments':
                article_id = data.get('article_id')
                article = KnowledgeArticle.objects.get(id=article_id)
                comments = article.comments.filter(is_approved=True).select_related('author')
                
                results = [{
                    'id': comment.id,
                    'content': comment.content,
                    'author': comment.author.username,
                    'created_at': comment.created_at.isoformat(),
                    'parent_id': comment.parent_id
                } for comment in comments]
                
                return JsonResponse({'comments': results})
            
            else:
                return JsonResponse({'error': 'Unknown action'}, status=400)
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'POST required'}, status=405)
