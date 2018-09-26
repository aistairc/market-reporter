function addCondition(queryField, queryRelation, queryVal) {
  let selectField = document.createElement('select');
  selectField.name = 'field';
  selectField.className = 'form-control';
  selectField.style = 'margin-right: 10px';

  const uri = new URI(window.location.href.toString());
  const fieldsHumanEvaluation = [
    'article_id',
    't',
    'phase',
    'note',
    'is_target'
  ];
  const fields = fieldsHumanEvaluation;
  fields.forEach(field => {
    let option = document.createElement('option');
    option.value =  field;
    option.textContent = field;
    selectField.appendChild(option);
    selectField.value = queryField;
  });

  let selectRelation = document.createElement('select');
  selectRelation.name = 'rel';
  selectRelation.className = 'form-control';
  selectRelation.style = 'margin-right: 10px';

  const relations = [
    '=',
    '!=',
    '>',
    '>=',
    '<',
    '<=',
    'like',
    'not like',
    'is null',
    'is not null'
  ];
  relations.forEach(relation => {
    let option = document.createElement('option');
    option.value = relation;
    option.textContent = relation;
    selectRelation.appendChild(option);
  });
  selectRelation.value = queryRelation;
  selectRelation.addEventListener('change', e => {
    e.target.parentNode.querySelector('[name="val"]').disabled = ['is null', 'is not null'].indexOf(e.target.value) >= 0;
  });

  let input = document.createElement('input');
  input.name = 'val';
  input.className = 'form-control';
  input.type = 'text';
  input.value = queryVal;
  input.style = 'margin-right: 10px';
  input.disabled = ['is null', 'is not null'].indexOf(queryRelation) >= 0;

  let btnRemove = document.createElement('button');
  btnRemove.className = 'btn btn-outline-secondary';
  btnRemove.style = 'height: 36.5px;';
  btnRemove.type = 'button';
  btnRemove.textContent = '−';
  btnRemove.addEventListener('click', e => {
    e.target.parentNode.parentNode.remove();
    let btnAdd = document.getElementById('btn-add');
    btnAdd.style.display = 'block';
  });

  let inline = document.createElement('div');
  inline.name = 'condition';
  inline.className = 'form-inline';
  inline.appendChild(selectField);
  inline.appendChild(selectRelation);
  inline.appendChild(input);
  inline.appendChild(btnRemove);

  let formGroup = document.createElement('div');
  formGroup.className = 'form-group';
  formGroup.appendChild(inline);

  let fieldset = document.getElementById('fieldset');
  fieldset.appendChild(formGroup);

  let size = document.getElementById('fieldset').childElementCount;
  let btnAdd = document.getElementById('btn-add');
  if (size == 5) {
    btnAdd.style.display = 'none';
  }

}

function search() {
  let uri = new URI();
  let fieldset = document.getElementById('fieldset');
  let groups = fieldset.querySelectorAll('.form-group');
  uri = uri.removeSearch('page');
  [0, 1, 2, 3, 4].forEach(i => {
    uri = uri
      .removeSearch('field' + i)
      .removeSearch('rel' + i)
      .removeSearch('val' + i);
  });

  groups.forEach((group, i) => {
    const row = group.querySelector('.form-inline');
    const field = row.querySelector('[name="field"]').value;
    const relation = row.querySelector('[name="rel"]').value;
    const val = row.querySelector('[name="val"]').value;
    uri = uri
      .addSearch('field' + i, field)
      .addSearch('rel' + i, relation)
      .addSearch('val' + i, val);
  });
  window.location.href = uri.toString();
}

document.addEventListener('DOMContentLoaded', () => {

  document.querySelectorAll('.timestamp').forEach(element => {
    element.innerHTML = element.textContent.split(' ').join('<br/>');
  });

  const uri = new URI(window.location.href.toString());
  const q = uri.search(true);
  let hasQuery = false;
  [0, 1, 2, 3, 4].forEach(i => {
    let f = 'field' + i.toString();
    let r = 'rel' + i.toString();
    let v = 'val' + i.toString();
    if (f in q && r in q && v in q) {
      hasQuery = true;
      addCondition(q['field' + i.toString()], q['rel' + i.toString()], q['val' + i.toString()]);
    }
  });
  if (!hasQuery) {
    addCondition('article_id', '=', '');
  }

  let current_page = 'page' in q ? q['page'] : 1;

  let prev_page = parseInt(current_page, 10) - 1;
  document.querySelectorAll('.jump-to-prev').forEach(element => {
    if (!element.disabled) {
      element.href = uri.setSearch({'page': prev_page.toString()});
    }
  });

  let next_page = parseInt(current_page, 10) + 1;
  document.querySelectorAll('.jump-to-next').forEach(element => {
    if (!element.disabled) {
      element.href = uri.setSearch({'page': next_page.toString()});
    }
  });

});
