import { type HTMLAttributes, type TableHTMLAttributes, type ThHTMLAttributes, type TdHTMLAttributes } from 'react';
function Root(props: TableHTMLAttributes<HTMLTableElement>) { return <table {...props} className={['jobs-table',props.className].filter(Boolean).join(' ')} />; }
function Scroll(props: HTMLAttributes<HTMLDivElement>) { return <div {...props} className={['table-scroll',props.className].filter(Boolean).join(' ')} />; }
function Header(props: HTMLAttributes<HTMLTableSectionElement>) { return <thead {...props} />; }
function Body(props: HTMLAttributes<HTMLTableSectionElement>) { return <tbody {...props} />; }
function Row(props: HTMLAttributes<HTMLTableRowElement>) { return <tr {...props} />; }
function Head(props: ThHTMLAttributes<HTMLTableCellElement>) { return <th scope="col" {...props} />; }
function Cell(props: TdHTMLAttributes<HTMLTableCellElement>) { return <td {...props} />; }
export const Table = { Root, Scroll, Header, Body, Row, Head, Cell };
