from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import (
    QuizResult, QuizCategory, QuizQuestion, QuizAnswer, QuizSession,
    KnowledgeCategory, KnowledgeArticle, KnowledgeTag, KnowledgeComment
)
from .utils import process_article_content

class PlayerNameForm(forms.Form):
    player_name = forms.CharField(
        max_length=100,
        label='プレイヤー名',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    category = forms.ModelChoiceField(
        queryset=QuizCategory.objects.all(),
        label='カテゴリー',
        empty_label='カテゴリーを選択してください',
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'onchange': 'this.setAttribute("data-selected", "true")'
        })
    )

class QuizAnswerForm(forms.Form):
    def __init__(self, *args, **kwargs):
        question = kwargs.pop('question')
        super(QuizAnswerForm, self).__init__(*args, **kwargs)
        
        choices = [(answer.id, answer.answer_text) for answer in question.answers.all()]
        self.fields['answer'] = forms.ChoiceField(
            choices=choices,
            widget=forms.RadioSelect,
            label=question.question_text
        )

class QuizSessionForm(forms.Form):
    quiz_master = forms.CharField(
        max_length=100,
        label='クイズマスター名',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    category = forms.ModelChoiceField(
        queryset=QuizCategory.objects.all(),
        label='カテゴリー',
        empty_label='カテゴリーを選択してください',
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'onchange': 'this.setAttribute("data-selected", "true")'
        })
    )
    total_questions = forms.IntegerField(
        min_value=1,
        max_value=10,
        initial=5,
        label='問題数',
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

class JoinSessionForm(forms.Form):
    session_id = forms.UUIDField(
        label='セッションID',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    player_name = forms.CharField(
        max_length=100,
        label='プレイヤー名',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )


class KnowledgeArticleForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=KnowledgeTag.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select relevant tags for this article"
    )
    
    class Meta:
        model = KnowledgeArticle
        fields = ['title', 'slug', 'content', 'summary', 'category', 'tags', 'status', 'featured']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter article title'
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'article-url-slug'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control rich-text-editor',
                'rows': 15,
                'placeholder': 'Write your article content here...',
                'data-editor': 'tinymce'
            }),
            'summary': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Brief summary of the article'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'featured': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = KnowledgeCategory.objects.all()
        self.fields['category'].empty_label = "Select a category"
    
    def clean_content(self):
        """Sanitize and validate article content for security."""
        content = self.cleaned_data.get('content')
        
        if not content:
            raise ValidationError("Article content is required.")
        
        processed_content, is_valid, error_message = process_article_content(content)
        
        if not is_valid:
            raise ValidationError(error_message)
        
        return processed_content
    
    def clean_title(self):
        """Validate article title."""
        title = self.cleaned_data.get('title')
        
        if not title:
            raise ValidationError("Article title is required.")
        
        if len(title.strip()) < 5:
            raise ValidationError("Article title must be at least 5 characters long.")
        
        if len(title) > 200:
            raise ValidationError("Article title cannot exceed 200 characters.")
        
        if any(char in title for char in ['<', '>', '"', "'"]):
            raise ValidationError("Article title contains invalid characters.")
        
        return title.strip()
    
    def clean_summary(self):
        """Validate article summary."""
        summary = self.cleaned_data.get('summary')
        
        if summary and len(summary.strip()) < 10:
            raise ValidationError("Article summary must be at least 10 characters long.")
        
        if summary and len(summary) > 500:
            raise ValidationError("Article summary cannot exceed 500 characters.")
        
        return summary.strip() if summary else summary


class KnowledgeCategoryForm(forms.ModelForm):
    class Meta:
        model = KnowledgeCategory
        fields = ['name', 'description', 'parent']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Category name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe this category'
            }),
            'parent': forms.Select(attrs={
                'class': 'form-select'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['parent'].queryset = KnowledgeCategory.objects.all()
        self.fields['parent'].empty_label = "No parent category"
        self.fields['parent'].required = False


class KnowledgeTagForm(forms.ModelForm):
    class Meta:
        model = KnowledgeTag
        fields = ['name', 'color']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tag name'
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color',
                'value': '#007bff'
            })
        }


class KnowledgeCommentForm(forms.ModelForm):
    class Meta:
        model = KnowledgeComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Write your comment here...'
            })
        }


class KnowledgeSearchForm(forms.Form):
    query = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search articles...',
            'autocomplete': 'off'
        })
    )
    category = forms.ModelChoiceField(
        queryset=KnowledgeCategory.objects.all(),
        required=False,
        empty_label="All categories",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    tags = forms.ModelMultipleChoiceField(
        queryset=KnowledgeTag.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        })
    )
    status = forms.ChoiceField(
        choices=[('', 'All statuses')] + KnowledgeArticle.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    author = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        empty_label="All authors",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
