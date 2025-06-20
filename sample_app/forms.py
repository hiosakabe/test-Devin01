from django import forms
from .models import QuizResult, QuizCategory, KaraokeScore

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

class KaraokeScoreForm(forms.ModelForm):
    class Meta:
        model = KaraokeScore
        fields = [
            'player_name', 'song_title', 'artist_name',
            'total_score', 'pitch_score', 'stability_score', 
            'expression_score', 'long_tone_score', 'technique_score',
            'overall_comment', 'kobushi_count', 'shakuri_count', 'vibrato_count'
        ]
        widgets = {
            'player_name': forms.TextInput(attrs={'class': 'form-control'}),
            'song_title': forms.TextInput(attrs={'class': 'form-control'}),
            'artist_name': forms.TextInput(attrs={'class': 'form-control'}),
            'total_score': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'max': '100.000'}),
            'pitch_score': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'max': '40.000'}),
            'stability_score': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'max': '30.000'}),
            'expression_score': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'max': '15.000'}),
            'long_tone_score': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'max': '10.000'}),
            'technique_score': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'max': '5.000'}),
            'overall_comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'kobushi_count': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'shakuri_count': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'vibrato_count': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }
