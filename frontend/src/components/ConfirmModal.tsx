import React from 'react';

interface ConfirmModalProps {
  title: string;
  body: string;
  confirmLabel?: string;
  danger?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

export const ConfirmModal: React.FC<ConfirmModalProps> = ({
  title,
  body,
  confirmLabel = 'Подтвердить',
  danger,
  onCancel,
  onConfirm,
}) => {
  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div className="modal-card" onClick={(event) => event.stopPropagation()}>
        <h3>{title}</h3>
        <p>{body}</p>
        <div className="modal-actions">
          <button className="btn-outline" type="button" onClick={onCancel}>
            Отмена
          </button>
          <button className={danger ? 'btn-danger' : 'btn-primary'} type="button" onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};
