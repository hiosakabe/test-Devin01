from django import forms
from .models import QuizResult, QuizCategory

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
        widget=forms.Select(attrs={'class': 'form-control'})
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
